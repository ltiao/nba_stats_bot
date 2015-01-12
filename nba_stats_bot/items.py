# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy

from scrapy.contrib.djangoitem import DjangoItem
from nba.models import Player, Team

class PlayerItem(DjangoItem):
	django_model = Player

	file_urls = scrapy.Field()
	files = scrapy.Field()

class TeamItem(DjangoItem):
	django_model = Team

	file_urls = scrapy.Field()
	files = scrapy.Field()

class CrappyItem(scrapy.Item):

    first_name = scrapy.Field()
    last_name = scrapy.Field()

class ArenaItem(scrapy.Item):

	name = scrapy.Field()
	capacity = scrapy.Field()
