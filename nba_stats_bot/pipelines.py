# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import functools
import django

from scrapy import log
from nba.models import Player, School

django.setup()

def selective(process_item_func):

    @functools.wraps(process_item_func)
    def wrapper(self, item, spider):

        msg = '{{}} {} pipeline step: "{}" {{}}in {}' \
            .format(self.__class__.__name__, spider.name, self.spiders)

        if spider.name in self.spiders:
            spider.log(msg.format('executing', ''), level=log.DEBUG)
            item = process_item_func(self, item, spider)
        else:
            spider.log(msg.format('skipping', 'not '), level=log.DEBUG)
        
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
        item_dict = dict(item)

        if 'school' in item_dict:
            school_name = item_dict.get('school')
            if school_name is not None:
                if school_name in ('', ' ', '-', 'No College'):
                    item_dict['school'] = None
                else:
                    school_obj, created = School.objects.get_or_create(name=school_name)
                    item_dict['school'] = school_obj

        player_obj, _ = Player.objects.update_or_create(nba_id=item_dict.get('nba_id'), defaults=item_dict)
        
        return item

