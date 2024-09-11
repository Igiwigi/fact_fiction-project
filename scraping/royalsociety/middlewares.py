# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from scrapy import signals

# useful for handling different item types with a single interface
from itemadapter import is_item, ItemAdapter
import undetected_chromedriver as uc
from scrapy.http import HtmlResponse

class RoyalsocietySpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)

import logging
from scrapy.http import HtmlResponse
from seleniumbase import SB
from urllib.parse import urlparse, urlunparse
import os
import re

class SeleniumBaseMiddleware:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.visited_urls = set()
        self.load_visited_urls()
        self.consecutive_non_doi = 0
        self.max_consecutive_non_doi = 200  #just to make sure it stops eventually when it runs out of doi pages (incase it doesnt, unclear)

    def normalize_url(self, url):
        """Normalize the URL by removing the fragment part."""
        parsed_url = urlparse(url)
        normalized_url = urlunparse(parsed_url._replace(fragment=''))
        return normalized_url

    def verify_success(self, sb):
        sb.assert_element('img[src="/pb-assets/journals-logos/rsta-1540911457623.svg"]', timeout=4)

    def load_visited_urls(self):
        if os.path.exists('visited_urls.csv'):
            with open('visited_urls.csv', 'r') as f:
                self.logger.info("Opening the visited URLs CSV file.")
                for line in f:
                    url = line.strip().strip('"')
                    self.visited_urls.add(url)
            self.logger.info(f"Total number of visited URLs loaded: {len(self.visited_urls)}")
        else:
            self.logger.info("No visited URLs file found. Starting with an empty set.")

    def is_doi_page(self, url):
        """Check if the URL is a DOI page."""
        return bool(re.search(r'/doi/10\.1098/rsta', url))
    
    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls()
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        return middleware

    def spider_opened(self, spider):
        self.crawler = spider.crawler

    def process_request(self, request, spider):
        normalized_url = self.normalize_url(request.url)

        if normalized_url in self.visited_urls:
            self.logger.info(f"Skipping already visited DOI (from some other run): {normalized_url}")
            return None

        with SB(uc=True, headless2=True) as sb: #with SB(uc=True, agent=user_agent) as sb: maybe another user agent
            sb.uc_open_with_reconnect(request.url, 3)
            try:
                self.verify_success(sb)
            except Exception:
                if sb.is_element_visible('input[value*="Verify"]'):
                    sb.uc_click('input[value*="Verify"]')
                elif sb.is_element_visible('iframe'):
                    sb.uc_gui_click_captcha()
                
                try:
                    self.verify_success(sb)
                except Exception as e:
                    raise Exception("Page verification failed after CAPTCHA handling!") from e

            source = sb.get_page_source()

        if self.is_doi_page(normalized_url):
            self.consecutive_non_doi = 0
        else:
            self.consecutive_non_doi += 1
            if self.consecutive_non_doi >= self.max_consecutive_non_doi:
                self.logger.warning(f"Reached {self.max_consecutive_non_doi} consecutive non-DOI pages. Stopping the spider.")
                self.crawler.engine.close_spider(spider, f"Reached {self.max_consecutive_non_doi} consecutive non-DOI pages")
                return None

        return HtmlResponse(normalized_url, encoding='utf-8', body=source, request=request)


