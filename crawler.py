import re
import argparse
import logging
from requests.utils import urlparse, urlunparse
from requests.compat import urljoin
import requests

logging.basicConfig(filename='error.log')


class Crawler(object):

    LINK = re.compile('<a [^>]*href=[\'|"](.*?)[\'"][^>]*?>')

    FILE_CONTENTS = (".epub", ".mobi", ".docx", ".doc", ".opf", ".7z", ".ibooks", ".cbr",
                     ".avi", ".mkv", ".mp4", ".jpg", ".jpeg", ".png", ".gif",".pdf",
                     ".iso", ".rar", ".tar", ".tgz", ".zip", ".dmg", ".exe")

    def __init__(self, domain, query=False, fragment=False, fallback_scheme='https'):

        self.fallback_scheme = fallback_scheme
        self.rooturl = self.prepare_root_url(domain)

        self.query = query
        self.fragment = fragment

        self.todo_urls = set()
        self.done_urls = set()

    def start(self):
        """
        Calling this method starts crawling pages
        :return:
        """

        self.get_first_page()

        while len(self.todo_urls):
            url = self.todo_urls.pop()
            res = self.get_page_html(url)
            self.done_urls.add(url)
            if res:
                self.extract_urls(url, res.text)
            self.record_url(url)

    def prepare_root_url(self, domain):
        """
        Add scheme to domain if it's missing.

        ex. example.com => http://example.com or https://example.com
        ex. example.com/about => http://example.com/about or https://example.com/about

        scheme is set to fallback_scheme

        :param domain:
        :return:
        """

        rooturl = urlparse(domain)

        if rooturl.scheme == "":
            l_url = list(rooturl)
            if rooturl.netloc == "":
                if rooturl.path == "":
                    raise ValueError("Invalid domain {}".format(domain))

                domain = domain.split('/')
                l_url[1] = domain[0]
                if len(domain) > 1:
                    l_url[2] = "/".join(domain[1:])
                else:
                    l_url[2] = ""

            l_url[0] = self.fallback_scheme
            return urlparse(urlunparse(l_url))
        else:
            return rooturl

    def get_first_page(self):
        """
        Apart from crawling first page this method also sets correct (correct url scheme) domain url.

        ex. if user provides domain with http however server redirects to https url then this also
        updates rooturl with https scheme and therefore avoiding additional redirect caused due to
        incorrect scheme for all other subsequent requests.
        :return:
        """
        url = self.rooturl.geturl()
        try:
            res = self._get_page(url)
        except Exception as e:
            logging.exception("domain error {}".format(url))
            return

        self.done_urls.add(url)
        if 299 >= res.status_code >= 200:
            # check if there was redirect on first page
            # if so then update rooturl
            # this will also set correct url scheme which will be used by subsequent requests.
            # correct scheme will avoid additional redirect (most cases it's redirect from http to https)
            new_url = url
            if len(res.history) > 0:
                new_url = res.url
                self.rooturl = urlparse(new_url)
                self.done_urls.add(new_url)

            self.extract_urls(new_url, res.text)
            self.record_url(new_url)

    @staticmethod
    def _get_page(url):
        return requests.get(url)

    def get_page_html(self, url):
        """
        :param url: Page url to fetch
        :return: Returns result as bytes
        """
        try:
            res = self._get_page(url)
            if 299 >= res.status_code >= 200:
                return res
            return None
        except Exception as e:
            return None

    def record_url(self, url):
        """

        :param url: Url to print or add in xml file
        :return:
        """
        print(url)

    def extract_urls(self, current_url, html):
        """

        :param current_url: page url from which urls need to be extracted.
        :param html: actual page html to crawl for urls.
        :return:
        """
        if html:
            raw_links = self.LINK.findall(html)
            for raw_link in raw_links:
                raw_link = raw_link
                link = self.prepare_url(current_url, raw_link)

                if link and link not in self.done_urls:
                    self.todo_urls.add(link)

    def prepare_url(self, current_url, url):
        """
        This prepares crawled url with proper format
        1. This adds scheme to urls which starts with / or //
        2. Discards external urls, mailto links, tel links, fax links
        3. Removes fragment or query part based on setting.
        4. converts relative url to absolute url

        :param current_url:
        :param url:
        :return:
        """
        if isinstance(current_url, str):
            current_url = urlparse(current_url)

        if url in ("", "/", "./"):
            return None

        elif url.startswith(("mailto", "tel", "fax")):
            return None

        elif url.startswith("javascipt:"):
            return None

        elif url.startswith(('./', '../')):
            # convert relative url to absolute
            # ex. if current_url is http://example.com/about/ and
            #       1. url is ../careers then absolute url will be
            #           http://example.com/careers
            #       2 url is ./careers then absolute url will be
            #           http://example.com/about/careers

            url = urljoin(current_url.geturl(), url)

        elif url.startswith("#"):
            # 'http://www.gurlge.com:80/path/file.html;params?a=1#fragment'

            url = "{}://{}{};{}{}#{}".format(current_url.scheme,
                                             current_url.netloc,
                                             current_url.path,
                                             current_url.params,
                                             current_url.query,
                                             url)

        elif url.startswith("/"):
            url = urljoin("{}://{}".format(
                current_url.scheme,
                current_url.netloc),
                url)

        elif url.startswith("//"):
            url = url.replace("//", "/")
            url = "{}://{}".format(current_url.scheme, url)

        elif not url.startswith(("http", "https")):
            url = urljoin("{}://{}/".format(current_url.scheme, current_url.netloc), url)

        url = urlparse(url)

        if url.path.endswith(self.FILE_CONTENTS):
            return None

        if not self.is_valid_url(url):
            return None

        l_url = list(url)

        if not self.query:
            # Remove query string
            # [scheme, netloc, path, params, query, fragment]
            l_url[4] = ''

        if not self.fragment:
            # Remove fragment
            # [scheme, netloc, path, params, query, fragment]
            l_url[5] = ''

        # reconstruct url
        url = urlunparse(l_url)

        return url

    def is_valid_url(self, url):
        """
        Check is url belongs to same domain
        :param url:
        :return:
        """
        if isinstance(url, str):
            url = urlparse(url)

        if self.rooturl.netloc == url.netloc:
            return True
        return False

    def make_report(self):
        pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Sitemap crawler')

    parser.add_argument('--domain', required=True, action="store", default="",
                        help="target domain (ex: http://example.com)")

    parser.add_argument('--query', action="store_true", default=False,
                        help="retain query string (ex. '?a=1' will retained for url http://example.com?a=1)")

    parser.add_argument('--fragment', action="store_true", default=False,
                        help="retain fragment (ex. '#ascsort' will retained for url http://example.com#ascsort)")

    arg = vars(parser.parse_args())

    cwrl = Crawler(**arg)
    cwrl.start()
