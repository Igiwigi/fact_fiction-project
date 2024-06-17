import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
import os, requests, re

#add a check that skips links that weve already seen

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


class RoyalSocietySpider(CrawlSpider):
    name = 'royalsociety_spider'
    allowed_domains = ['royalsocietypublishing.org']
    #start_urls = ['https://royalsocietypublishing.org/loi/rstl/group/c1700.d1750.y1750']
    #start_urls = ["https://royalsocietypublishing.org/loi/rstl/group/c1800.d1800.y1800"]
    start_urls = ["https://royalsocietypublishing.org/loi/rstb/group/c1600.d1660.y1665"] 
    custom_settings = {
        'FEEDS': {'royalsociety.csv': {'format': 'csv'}}
    }
    visited_urls = set()


    #start https://royalsocietypublishing.org/loi/rstl/group/c1600.d1660.y1665
    #next https://royalsocietypublishing.org/toc/rstl/1666/1/20
    #then after https://royalsocietypublishing.org/doi/10.1098/rstl.1665.0128

    #rules = (
        # Rule to follow links to the second layer (TOC pages)
    #    Rule(LinkExtractor(allow=r'/toc/rstl/\d+/\d+')),
    #   Rule(LinkExtractor(allow=r'/toc/rstl/\d+/\d+/\d+')),
    # Rule(LinkExtractor(allow=r'/doi/10.1098/rstl.\d+.\d+')),
    #)

    rules = (
        Rule(LinkExtractor(allow=r'/toc/rstb/\d+/\d+')),
        Rule(LinkExtractor(allow=r'/toc/rstb/\d+/\d+/\d+')),
        Rule(LinkExtractor(allow=r'/toc/rstb*')),
        Rule(LinkExtractor(allow=r'/doi/10.1098/rstb.\d+.\d+'), callback = 'parse_intro_page'),
        Rule(LinkExtractor(allow=r'/toc/rstl/\d+/\d+')),
       Rule(LinkExtractor(allow=r'/toc/rstl/\d+/\d+/\d+')),
       Rule(LinkExtractor(allow=r'/doi/10.1098/rstl.\d+.\d+')),
    )

    
    def parse_intro_page(self, response):
        self.logger.info("Hi, this is an article page! %s length of visited %s", response.url, len(self.visited_urls))

        current_url_str = str(response.url)

        if  current_url_str in self.visited_urls:
            self.logger.info("Skipping scraping of already visited URL: %s", response.url)
            return
    
        item = MyItem() #creating an item

        item['author'] = response.css('.author-name::attr(title)').extract_first(default='none')
        item['publisher'] = response.css('meta[name="dc.Publisher"]::attr(content)').get()
        item['date'] = response.css('meta[name="dc.Date"]::attr(content)').get()
        item['identifier'] = response.css('meta[name="dc.Identifier"]::attr(content)').get()
        item['og_url'] = response.css('meta[property="og:url"]::attr(content)').get()
        item['title'] = re.sub(r'[\\/:*?"<>|]', '', response.css('meta[name="dc.Title"]::attr(content)').get()) #used to name download file, sanitized with resub so the file name is ok
        item['language'] = response.css('meta[name="dc.Language"]::attr(content)').get()
        item['pdf_link'] = response.css('a:contains("View PDF")::attr(href)').get() #gets the pdf link

        #download each pdf so we can scrape them later
        if 'og_url' in item:
            item['pdf_download_link'] = self.convert_to_download_link(item['og_url']) 
            #if 'pdf_download_link' in item:
                #yield scrapy.Request(item['pdf_download_link'], callback=self.save_pdf, meta={'filename': item['title']}) this doesnt work yet
        
        self.visited_urls.add(response.url)

        #this writes the item to csv if specified in command
        yield item

    #the logic by which download links are made (just changing the url)
    def convert_to_download_link(self, og_url):
        return og_url.replace("/doi/", "/doi/pdf/") + "?download=true"
    
    #https://royalsocietypublishing.org/doi/    10.1098/rstl.1665.0053               before 
    #https://royalsocietypublishing.org/doi/pdf/10.1098/rstl.1665.0053?download=true after

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_visited_urls()

    def load_visited_urls(self):
        # Load visited URLs from a file if it exists
        self.logger.info("HIHIHIHIHIHELLOHELLOHELLOH")
        if os.path.exists('visited_urls.csv'):
            with open('visited_urls.csv', 'r') as f:
                self.logger.info("Hi, opening the visited urls csv!")
                for line in f:
                    url = line.strip().strip('"')
                    self.visited_urls.add(url)
                    #self.logger.info("This line got added to be skipped %s", url)
                    #self.logger.info("length %s", len(self.visited_urls))
                #self.logger.info(self.visited_urls)


    def save_visited_urls(self):
        # Save visited URLs to a file
        with open('visited_urls.csv', 'w') as f:
            for url in self.visited_urls:
                f.write(url + '\n')

    def closed(self, reason):
        self.save_visited_urls()

    
    def save_pdf(self, response):
        self.logger.info("Hi, this is the link we are trying to download from! %s", response.url)
        
        filename = response.meta['filename'][:250]  # Limiting filename to 250 characters
        folder_path = 'pdfs'
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        # Saving the file
        with open(os.path.join(folder_path, filename + ".pdf"), 'wb') as f:
            f.write(response.body)
        
