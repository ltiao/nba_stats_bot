# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy

from scrapy.contrib.djangoitem import DjangoItem
from nba.models import Player

class PlayerItem(DjangoItem):
	django_model = Player

class CrappyItem(scrapy.Item):

    first_name = scrapy.Field()
    last_name = scrapy.Field()
