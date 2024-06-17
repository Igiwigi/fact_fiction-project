# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import csv

class RoyalsocietyPipeline:
    def __init__(self):
        self.csv_file = open('items.csv', 'a+', newline='', encoding='utf-8')
        self.csv_writer = None
        self.visited_urls = set()

        # If the file is not empty, load visited URLs into memory
        self.load_visited_urls()

    def process_item(self, item, spider):
        url = item.get('url')
        if url in self.visited_urls:
            # Skip processing item if URL has been visited
            return item

        # If URL is not visited, process the item
        if self.csv_writer is None:
            self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=item.keys())
            self.csv_writer.writeheader()
        self.csv_writer.writerow(item)

        # Add URL to visited set
        self.visited_urls.add(url)

        return item

    def close_spider(self, spider):
        self.csv_file.close()

    def load_visited_urls(self):
        self.csv_file.seek(0)
        reader = csv.DictReader(self.csv_file)
        for row in reader:
            self.visited_urls.add(row.get('url'))

