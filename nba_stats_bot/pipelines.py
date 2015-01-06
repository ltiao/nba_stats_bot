# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import functools
from scrapy import log

def selective(process_item_func):

    @functools.wraps(process_item_func)
    def wrapper(self, item, spider):

        msg = '{{}} {} pipeline step: "{}" {{}} {}' \
            .format(self.__class__.__name__, spider.name, self.spiders)

        if spider.name in self.spiders:
            spider.log(msg.format('executing', 'in'), level=log.DEBUG)
            item = process_item_func(self, item, spider)
        else:
            spider.log(msg.format('skipping', 'not in'), level=log.DEBUG)
        
        return item

    return wrapper

class PlayerPipeline(object):

    spiders = ['players']

    def __init__(self):
        pass

    def open_spider(self, spider):
        pass

    def close_spider(self, spider):
        pass

    @selective
    def process_item(self, item, spider):
        return item

