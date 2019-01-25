# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html

import logging
import pymongo
import items

class AssetstorebotPipeline(object):
    def __init__(self):
        self.client = pymongo.MongoClient('localhost', 27017)
        self.db = self.client['asset_store']
        self.col = self.db['packs']
        self.col.create_index('uri')


    def process_item(self, item, spider):
        if isinstance(item, items.AssetstorebotItem):
            try:
                self.col.update_one({'uri':item['uri']},
                                    {"$set":dict(item)},
                                    upsert=True)
            except Exception as ex:
                logging.error('update item failed:%s', ex)
        else:
            logging.warning('unknown item:%s[%s]', item, type(item))
        return item
