from __future__ import print_function
import sys
import time
from threading import Thread, Event, Lock
from argparse import ArgumentParser
from requests.utils import urlparse, urlunparse
from requests.compat import urljoin
import requests
import logging
from collections import defaultdict
from bs4 import BeautifulSoup

IS_PY2 = sys.version_info < (3, 0)

if IS_PY2:
    from robotparser import RobotFileParser
else:
    from urllib.robotparser import RobotFileParser


logging.basicConfig(filename='error.log', filemode='w')

FILE_CONTENTS = (".epub", ".mobi", ".docx", ".doc", ".opf", ".7z",
                 ".ibooks", ".cbr", ".avi", ".mkv", ".mp4", ".jpg",
                 ".jpeg", ".png", ".gif", ".pdf", ".iso", ".rar", ".tar",
                 ".tgz", ".zip", ".dmg", ".exe")

lock = Lock()


class Sitemap(object):
    def __init__(self, urls):
        self.urls = urls
        self.root = None
        self.domain = None

        if len(urls):
            url = urlparse(self.urls[0])
            self.domain = url.scheme + '://' + url.netloc
            self._prepare_site_map()

    @staticmethod
    def _get_path_node():
        """

        :return: defaultdict with defaultdict as default value
        """
        return defaultdict(defaultdict)

    def _prepare_site_map(self):
        """
        This generates site map tree and sets self.root to point to it.
        :return:
        """
        self.root = self._get_path_node()

        for url in self.urls:

            inner_root = self.root
            url = urlparse(url)
            paths = url.path.split('/')

            if paths[0] == '':
                paths = paths[1:]

            for path in paths:
                node = inner_root.get(path, None)
                if node:
                    inner_root = node
                    continue
                node = self._get_path_node()
                inner_root[path] = node
                inner_root = node

    def print_plain(self):
        """
        This prints site maps urls as a list
        :return:
        """
        print('\nUrls for domain', self.domain, end='\n\n')
        if self.urls:
            for url in self.urls:
                print(url)

    def print_tree(self):
        """
        This prints site maps urls as a tree
        :return:
        """
        print('\nSitemap for domain', self.domain, end='\n\n')

        def print_inner(_path, _node, depth=0):
            print(_path, end='')
            depth += len(_path) + 1
            node_len = len(_node)
            if node_len == 0:
                print('')
                return
            elif node_len == 1:
                print('/', end='')
                p = list(_node.keys())[0]
                n = list(_node.values())[0]
                print_inner(p, n, depth=depth)
            else:
                print('/')
                for p, n in _node.items():
                    print(' ' * depth, end='')
                    print_inner(p, n, depth=depth)

        if self.root:
            for path, node in self.root.items():
                print_inner(path, node)


class PageCrawler(Thread):
    def __init__(self, root_url, todo_urls, crawled_urls, urls_found,
                 stop_crawler_event, query=False, fragment=False, robot_parser=None):
        Thread.__init__(self)
        self.root_url = root_url
        self.todo_urls = todo_urls
        self.crawled_urls = crawled_urls
        self.urls_found = urls_found
        self.stop_crawler_event = stop_crawler_event
        self.query = query
        self.fragment = fragment
        self.robot_parser = robot_parser
        self._waiting = False

    @property
    def is_waiting(self):
        """
        Returns if thread is waiting for url to crawl.
        :return:
        """
        return self._waiting

    def run(self):
        """
        This method loop until stop_crawler_event is set.
        Get url from todo urls => download page => extract urls and repeat.
        :return:
        """
        while not self.stop_crawler_event.is_set():
            try:
                with lock:
                    url = self.todo_urls.pop()
                    self._waiting = False
            except KeyError:
                self._waiting = True
            else:
                if url in self.crawled_urls:
                    continue

                res = self.get_page_html(url)

                self.crawled_urls.add(url)
                if res:
                    self.extract_urls(url, res.text)

    @staticmethod
    def _get_page(url):
        """
        Gets response from internet

        :param url: Url to fetch
        :return: Returns response object if request was successful.
        """
        return requests.get(url)

    def get_page_html(self, url):
        """

        :param url: Page url to fetch
        :return: Returns result as string for successful response
        else None in case of unsuccessful response or exception.
        """
        try:
            res = self._get_page(url)
            if 299 >= res.status_code >= 200:
                return res
            return None
        except requests.exceptions.RequestException as e:
            return None

    def prepare_url(self, current_url, url):
        """
        This prepares crawled url with proper format
        1. This adds scheme to urls which starts with / or //
        2. Discards external urls, mailto links, tel links, fax links
        3. Removes fragment or query part based on setting.
        4. converts relative url to absolute url

        :param current_url: Current page url
        :param url: Url crawled from current page this url can be anything
                ex. relative url, external url
        :return: Returns absolute url of crawled url as per settings.
        """
        if IS_PY2:
            if isinstance(current_url, basestring):
                current_url = urlparse(current_url)
        else:
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
            url = urljoin("{}://{}/".format(current_url.scheme,
                                            current_url.netloc),
                          url)

        url = urlparse(url)

        if url.path.endswith(FILE_CONTENTS):
            return None

        if self.is_external_url(url):
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

    def is_external_url(self, url):
        """
        Check if url belongs to same domain.

        :param url: Url to check for.
        :return: False if url belongs to same domain else True.
        """
        if isinstance(url, str):
            url = urlparse(url)

        if self.root_url.netloc == url.netloc:
            return False
        return True

    def extract_urls(self, current_url, html):
        """
        Extract urls from html page and save then for processing if url is not
        processed before. Url will be ignored if it's already processed.
        This will also print current status of found, visited, yet to visit
        urls

        :param current_url: page url from which urls need to be extracted.
        :param html: actual page html to crawl for urls.
        :return: None
        """
        if html:
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all('a', href=True):
                raw_link = a['href']
                link = self.prepare_url(current_url, raw_link)

                if not self.can_fetch(link):
                    continue

                if link and link not in self.crawled_urls:
                    with lock:
                        self.todo_urls.add(link)
                        self.urls_found.add(link)

            print('urls found: {}, urls visited: {}, urls to visit: {}'.format(
                len(self.urls_found), len(self.crawled_urls),
                len(self.todo_urls)))

    def can_fetch(self, link):
        if self.robot_parser:
            try:
                if self.robot_parser.can_fetch("*", link):
                    return True
                else:
                    return False
            except:
                return True
        return True


class Crawler(object):
    def __init__(self, domain, limit=1000, jobs=16, query=False,
                 fragment=False, fallback_scheme='http'):

        self.limit = limit

        self.query = query

        self.fragment = fragment

        self.jobs = jobs

        self.fallback_scheme = fallback_scheme

        self.root_url = self.prepare_root_url(domain)

        # url which are not visited yet
        self.todo_urls = set()

        # visited urls
        self.crawled_urls = set()

        # urls found for site map
        self._urls_found = set()

        self.crawler_jobs = []

        self.stop_crawler_event = Event()

        self.rp = None

    @property
    def urls_found(self):
        """
        This returns list of found urls.
        :return: list of urls
        """
        if self.limit < 0:
            return list(self._urls_found)
        else:
            return list(self._urls_found)[:self.limit]

    def start(self):
        """
        This method will launch crawler threads.
        :return:
        """
        self.get_real_domain()
        self.get_robot_txt()
        for i in range(0, self.jobs):
            t = PageCrawler(self.root_url,
                            self.todo_urls,
                            self.crawled_urls,
                            self._urls_found,
                            self.stop_crawler_event,
                            self.query,
                            self.fragment,
                            self.rp
                            )

            self.crawler_jobs.append(t)
            t.start()

        while 1:
            time.sleep(0.1)
            if self.is_finished():
                self.stop_crawler_event.set()
                break

        for job in self.crawler_jobs:
            job.join()

    def is_finished(self):
        """
        This will return true if site map completion condition is reached.
        :return:
        """

        # If all threads are dead then tell main thread to finish the crawling
        # process.
        if all([not job.is_alive() for job in self.crawler_jobs]):
            return True

        with lock:
            # limit is negative (i.e don't stop until all pages are crawled)
            # and todo_url list reached to 0 and all threads are waiting for
            # urls
            if self.limit < 0 and len(self.todo_urls) == 0 and \
                    all([job.is_wating for job in self.crawler_jobs]):
                return True

            # limit is positive (i.e stop if urls_found equals limit)
            # or todo_url list reached to 0 and all threads are waiting for
            # urls.
            elif len(self._urls_found) >= self.limit or (
                        len(self.todo_urls) == 0 and
                        all([job.is_waiting for job in self.crawler_jobs])):
                return True

        return False

    def prepare_root_url(self, domain):
        """
        Add scheme to domain if it's missing.

        ex. example.com => http://example.com or https://example.com
        ex. example.com/about => http://example.com/about or
                https://example.com/about

        scheme is set to fallback_scheme

        :param domain: domain name provided by user with or without scheme
        :return: scheme qualified domain.
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

    def get_real_domain(self):
        """
        This method tries to get exact domain url.

        ex. if user provides domain with http however server redirects to
        https url then this also updates root_url with https scheme and
        therefore avoiding additional redirect caused due to incorrect scheme
        for all other subsequent requests.
        :return:
        """
        url = self.root_url.geturl()
        try:
            res = requests.request('HEAD', url)
        except requests.exceptions.RequestException as e:
            logging.exception("domain error {}".format(url))
            return

        if 299 >= res.status_code >= 200:
            # check if there was redirect on first page
            # if so then update root_url
            # this will also set correct url scheme which will be used by
            # subsequent requests.
            # correct scheme will avoid additional redirect (most cases it's
            # redirect from http to https)
            if len(res.history) > 0:
                new_url = res.url
                self.root_url = urlparse(res.url)
                self._urls_found.add(self.root_url.geturl())
                with lock:
                    self.todo_urls.add(new_url)

    def get_robot_txt(self):
        robots_url = urljoin(
            '{}://{}'.format(self.root_url.scheme, self.root_url.netloc),
            "robots.txt")
        self.rp = RobotFileParser()
        self.rp.set_url(robots_url)
        self.rp.read()

if __name__ == '__main__':

    parser = ArgumentParser(description='Sitemap crawler')

    parser.add_argument('--domain', required=True, action="store", default="",
                        help="target domain (ex: http://example.com)")

    parser.add_argument('--limit', action="store", default=1000, type=int,
                        help="limit the no. of urls in sitemap use -1 to "
                             "crawl all pages of domain")

    parser.add_argument('--jobs', required=False, action="store", type=int,
                        default=16, help="number of simultaneous jobs")

    parser.add_argument('--query', action="store_true", default=False,
                        help="retain query string (ex. '?a=1' will retained "
                             "for url http://example.com?a=1)")

    parser.add_argument('--fragment', action="store_true", default=False,
                        help="retain fragment (ex. '#ascsort' will retained "
                             "for url http://example.com#ascsort)")

    parser.add_argument('--plain', required=False, action="store_true",
                        default=False, help="prints result as plain urls"
                                            "instead of tree")

    args = vars(parser.parse_args())

    plain = args.pop('plain')

    cwrl = Crawler(**args)

    cwrl.start()

    s = Sitemap(cwrl.urls_found)

    if plain:
        s.print_plain()
    else:
        s.print_tree()
