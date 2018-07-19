import unittest
from crawler import Crawler


class PrepareRootUrlTest(unittest.TestCase):
    def setUp(self):
        self.crawler = Crawler(domain='example.com', fallback_scheme='https')
        # first url in tuple is input and second is expected output
        self.urls = [('example.com', 'https://example.com'),
                     ('example.com/about', 'https://example.com/about')]

    def test_prepare_root_url(self):
        for url, expected_url in self.urls:
            self.assertEqual(
                self.crawler.prepare_root_url(url).geturl(),
                expected_url)


class PrepareRootUrlTest(unittest.TestCase):
    def setUp(self):
        self.crawler = Crawler(domain='https://example.com')
        # first url is current page url
        # second url is crawled url in current page
        # third url is absolute url which is expected result
        self.urls = [
            ('https://example.com/', '/about', 'https://example.com/about'),
            ('https://example.com/', 'about/first',
             'https://example.com/about/first'),
            ('https://example.com/about/', '../first',
             'https://example.com/first'),
            ('https://example.com/about/', './first',
             'https://example.com/about/first'),
            ('https://example.com/about/', 'https://anotherexample.com', None),
            ('https://example.com/about/', '/download/example.pdf', None),
            ('https://example.com/', '/about?sort=1',
             'https://example.com/about'),
            ('https://example.com/', '/about?sort=1#linkicon',
             'https://example.com/about')]

    def test_prepare_url(self):
        for current_url, url, expected_url in self.urls:
            self.assertEqual(
                self.crawler.prepare_url(current_url, url),
                expected_url)


class PrepareRootUrlWithQueryTest(unittest.TestCase):
    def setUp(self):
        self.crawler = Crawler(domain='https://example.com', query=True)
        # first url is current page url
        # second url is crawled url in current page
        # third url is absolute url which is expected result

        self.urls = [
            ('https://example.com/about/', 'https://anotherexample.com?sort=1',
             None),
            ('https://example.com/about/', '/download/example.pdf?sort=1',
             None),
            ('https://example.com/', '/about?sort=1',
             'https://example.com/about?sort=1'),
            ('https://example.com/', '/about?sort=1#linkicon',
             'https://example.com/about?sort=1'),
            ('https://example.com/first/', '../about?sort=1',
             'https://example.com/about?sort=1'),
            ('https://example.com/first/', '../about?sort=1#linkicon',
             'https://example.com/about?sort=1')]

    def test_prepare_url(self):
        for current_url, url, expected_url in self.urls:
            self.assertEqual(
                self.crawler.prepare_url(current_url, url),
                expected_url)


class PrepareRootUrlWithfragmentTest(unittest.TestCase):
    def setUp(self):
        self.crawler = Crawler(domain='https://example.com', fragment=True)
        # first url is current page url
        # second url is crawled url in current page
        # third url is absolute url which is expected result

        self.urls = [
            ('https://example.com/about/',
             'https://anotherexample.com?sort=1#linkicon', None),
            ('https://example.com/about/',
             '/download/example.pdf?sort=1#linkicon', None),
            ('https://example.com/', '/about?sort=1#linkicon',
             'https://example.com/about#linkicon'),
            ('https://example.com/', '/about?#linkicon',
             'https://example.com/about#linkicon'),
            ('https://example.com/first/', '../about?#linkicon',
             'https://example.com/about#linkicon'),
            ('https://example.com/first/', '../about?sort=1#linkicon',
             'https://example.com/about#linkicon')]

    def test_prepare_url(self):
        for current_url, url, expected_url in self.urls:
            self.assertEqual(
                self.crawler.prepare_url(current_url, url),
                expected_url)


class IsExternalUrlTest(unittest.TestCase):
    def setUp(self):
        self.crawler = Crawler(domain='https://example.com')
        # first is crawled url
        # second is_external flag

        self.urls = [
            ('https://example.com/about/', False),
            ('https://anotherexample.com/', True),
            ('https://anotherexample.com/about/', True),
            ]

    def test_is_external_url(self):
        for url, is_external in self.urls:
            self.assertEqual(
                self.crawler.is_external_url(url),
                is_external)


if __name__ == '__main__':
    unittest.main()
