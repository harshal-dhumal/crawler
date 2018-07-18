from urllib.parse import urlparse, urlunparse
from urllib.request import urlopen
import re


class Crawler(object):

    LINK = re.compile(b'<a [^>]*href=[\'|"](.*?)[\'"][^>]*?>')

    def __init__(self, rooturl, exclude_query=True, exclude_fragment=True, output_file=None):
        self.rooturl = urlparse(rooturl)
        self.exclude_query = exclude_query
        self.exclude_fragment = exclude_fragment
        self.output_file = output_file

        self.todo_urls = set([rooturl])
        self.done_urls = set()

    def start(self):
        """
        Calling this method starts crawling pages
        :return:
        """
        if self.output_file:
            self.output_file = open(self.output_file, 'w')

        while len(self.todo_urls):
            url = self.todo_urls.pop()
            html = self.get_page_html(url)
            self.done_urls.add(url)
            if html:
                self.extract_urls(url, html)
            self.record_url(url)

    @staticmethod
    def get_page_html(url):
        """

        :param url: Page url to fetch
        :return: Returns result as bytes
        """
        try:
            res = urlopen(url)
            if 299 >= res.status >= 200:
                return res.read()
            return None
        except Exception as e:
            return None

    def record_url(self, url):
        """

        :param url: Url to print or add in xml file
        :return:
        """
        print(url)
        if self.output_file:
            print(url, file=self.output_file)

    def extract_urls(self, current_url, html):
        """

        :param current_url: page url from which urls need to be extracted.
        :param html: actual page html to crawl for urls.
        :return:
        """
        if html:
            raw_links = self.LINK.findall(html)
            for raw_link in raw_links:
                raw_link = raw_link.decode('utf-8')
                link = self.prepare_url(current_url, raw_link)

                if link and link not in self.done_urls:
                    self.todo_urls.add(link)

    def prepare_url(self, current_url, url):
        """
        This prepares crawled url with proper format
        1. This adds scheme to urls which starts with / or //
        2. Discards external urls, mailto links, tel links, fax links
        3. Removes fragment or query part bases on setting.

        :param current_url:
        :param url:
        :return:
        """
        if isinstance(current_url, str):
            current_url = urlparse(current_url)

        if url in ("", "/"):
            return None
        elif url.startswith(("mailto", "tel", "fax")):
            return None
        elif url.startswith("javascipt:"):
            return None
        elif url.startswith("#"):
            # 'http://www.gurlge.com:80/path/file.html;params?a=1#fragment'

            url = "{}://{}{};{}{}#{}".format(current_url.scheme,
                                             current_url.netloc,
                                             current_url.path,
                                             current_url.params,
                                             current_url.query,
                                             url)

        elif url.startswith("/"):
            url = "{}://{}{}".format(current_url.scheme,
                                     current_url.netloc,
                                     url)

        elif url.startswith("//"):
            url = url.replace("//", "/")
            url = "{}://{}".format(current_url.scheme, url)
        elif not url.startswith(("http", "https")):
            url = "{}://{}/{}".format(current_url.scheme, current_url.netloc, url)

        url = urlparse(url)

        if not self.is_valid_url(url):
            return None

        l_url = list(url)

        if self.exclude_query:
            # [scheme, netloc, path, params, query, fragment]
            l_url[4] = ''

        if self.exclude_fragment:
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
    cwrl = Crawler(rooturl='https://redhat.com')
    cwrl.start()
