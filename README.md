# crawler
Web crawler to generate Sitemap

# Usage

Crawl site with default options (limit 1000, jobs 16).  
**python crawler.py --domain 'example.com'**

or

Crawl site until 5000 urls found.  
**python crawler.py --domain 'http://example.com' --limit 5000**

or

Crawl site until 6000 urls found with 20 simultaneous jobs (threads)  
**python crawler.py --domain 'https://example.com' --limit 6000 --jobs 20**

or

Crawl site until 5000 urls found and print result as list of urls.  
**python crawler.py --domain 'https://example.com' --limit 5000 --plain**

# Running tests

python tests.py -v


# Help

python crawler.py --help


# Errors

refer error.log file if crawler fails to download first page.