# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class AssetstorebotItem(scrapy.Item):
    name = scrapy.Field()
    uri = scrapy.Field()
    price = scrapy.Field()
    rating_score = scrapy.Field()
    rating_count = scrapy.Field()
    publisher = scrapy.Field()
    category = scrapy.Field()
