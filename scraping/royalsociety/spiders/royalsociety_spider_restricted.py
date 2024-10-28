import scrapy
from scrapy.crawler import CrawlerProcess
import os
import re
import pandas as pd
import csv

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

class RoyalSocietySpider(scrapy.Spider):
    name = 'royalsociety_spider_restricted'
    custom_settings = {
        'FEEDS': {'royalsociety_restricted_results.csv': {'format': 'csv'}}
    }

    def __init__(self, *args, **kwargs):
        super(RoyalSocietySpider, self).__init__(*args, **kwargs)
        self.start_urls = self.load_urls_from_csv()

    def load_urls_from_csv(self):
        urls = []
        with open('restricted_urls.csv', 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if row:  # Check if the row is not empty
                    urls.append(row[0])  # Assume the URL is in the first column
        return urls

    def parse(self, response):
        access_type1 = response.css('span.citation__access__type.no-access::text').get(default='').strip()
        access_type2 = response.css('span.article__access__type.no-access::text').get(default='').strip()
        
        if access_type1 == "Restricted access" or access_type2 == "Restricted access":
            self.logger.info("Restricted access URL: %s", response.url)
            return
        
        item = MyItem()

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

        item['subjects'] = response.css('section.article__keyword .section__body .rlist li a::text').getall() or ['']
        item['keywords'] = [keyword.strip() for keyword in response.css('meta[name="keywords"]::attr(content)').get(default='').split(',')]

        if item.get('og_url'):
            item['pdf_download_link'] = self.convert_to_download_link(item['og_url']) 
        
        self.append_item_to_csv(item)

        yield item

    def convert_to_download_link(self, og_url):
        return og_url.replace("/doi/", "/doi/pdf/") + "?download=true"

    def append_item_to_csv(self, item):
        df = pd.DataFrame([item])
        file_exists = os.path.isfile('royalsociety_restricted_results_backup.csv')
        df.to_csv('royalsociety_restricted_results_backup.csv', mode='a', header=not file_exists, index=False)