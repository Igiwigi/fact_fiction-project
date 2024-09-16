import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
import os
import re
import pandas as pd

#works, albeit slow

#maybe rerun the other pages (rstb in particular) to see if any non-restricted pages are missing

class MyItem(scrapy.Item):
    author = scrapy.Field()
    publisher = scrapy.Field()
    date = scrapy.Field()
    identifier = scrapy.Field()
    og_url = scrapy.Field()
    title = scrapy.Field()
    language = scrapy.Field()
    pdf_link = scrapy.Field()
    pdf_download_link = scrapy.Field()
    subjects = scrapy.Field()
    keywords = scrapy.Field()
    

class RoyalSocietySpider(CrawlSpider):
    name = 'royalsociety_spider'
    allowed_domains = ['royalsocietypublishing.org']
    start_urls = ["https://royalsocietypublishing.org/toc/rsta1887/1887/178"] #doing rsta now
    custom_settings = {
        'FEEDS': {'royalsociety_rsta_checking_missing.csv': {'format': 'csv'}}
    }
    visited_urls = set()

    rules = (
    Rule(LinkExtractor(allow=r'/doi/10\.1098/rsta', deny=r'badge\.dimensions\.ai'), callback="parse_doi_page", follow=True),
    Rule(LinkExtractor(allow=r'/toc/rsta'), follow=True),
    Rule(LinkExtractor(allow=r'/loi/rsta'), follow=True),
    )

    def parse_doi_page(self, response):
        """Scrape the necessary data from the doi page, incl metadata & download link for later"""
        
        #clumsy but should be ok
        access_type1 = response.css('span.citation__access__type.no-access::text').get(default='').strip()
        access_type2 = response.css('span.article__access__type.no-access::text').get(default='').strip()
        
        if access_type1 == "Restricted access" or access_type2 == "Restricted access":
            self.logger.info("Skipping restricted access URL: %s", response.url)
            self.save_visited_url(response.url)
            self.save_restricted_url(response.url)
            return
        
        #skip if empty response body (already visited)
        if not response.body.strip():
            self.logger.info("Skipping empty response from URL (page already scraped): %s", response.url)
            return
                
        item = MyItem()

        #theres multiple different ways of listing authors, so I'm trying to cover all bases
        authors = response.css('meta[name="dc.Creator"]::attr(content)').getall()
        if authors:
            item['author'] = ' and '.join(authors)
        else:
            item['author'] = response.css('.author-name::attr(title)').extract_first(default='none')

        item['publisher'] = response.css('meta[name="dc.Publisher"]::attr(content)').get(default='dunno')
        item['date'] = response.css('meta[name="dc.Date"]::attr(content)').get(default='dunno')
        item['identifier'] = response.css('meta[name="dc.Identifier"]::attr(content)').get(default='dunno')
        item['og_url'] = response.url
        item['title'] = re.sub(r'[\\/:*?"<>|]', '', response.css('meta[name="dc.Title"]::attr(content)').get(default='dunno'))
        item['language'] = response.css('meta[name="dc.Language"]::attr(content)').get(default='dunno')
        item['pdf_link'] = response.css('a:contains("View PDF")::attr(href)').get(default='dunno')

        #these were added recently and miss from a lot of data! kind of problematic
        item['subjects'] = response.css('section.article__keyword .section__body .rlist li a::text').getall() or ['']
        item['keywords'] = [keyword.strip() for keyword in response.css('meta[name="keywords"]::attr(content)').get(default='').split(',')]

        if item.get('og_url'):
            item['pdf_download_link'] = self.convert_to_download_link(item['og_url']) 
        
        self.append_item_to_csv(item)
        self.save_visited_url(response.url)

        yield item

    def convert_to_download_link(self, og_url):
        return og_url.replace("/doi/", "/doi/pdf/") + "?download=true"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_visited_urls()

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

    def save_visited_url(self, url):
        """Appends each visited website to a CSV file."""
        with open('visited_urls.csv', 'a') as f:
            f.write(url + '\n')

    def save_restricted_url(self, url):
        """Appends each restricted website to a CSV file."""
        with open('restricted_urls.csv', 'a') as f:
            f.write(url + '\n')

    def append_item_to_csv(self, item):
        """Appends to a dataframe so I can rest assured the data *is* somewhere even if the item pipeline doesn't work."""
        df = pd.DataFrame([item])
        file_exists = os.path.isfile('royalsociety_rsta_checking_missing2.csv')
        df.to_csv('royalsociety_rsta_checking_missing2.csv', mode='a', header=not file_exists, index=False)

