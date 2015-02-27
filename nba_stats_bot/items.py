# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy

from scrapy.contrib.djangoitem import DjangoItem
from nba.models import Player, Team, Game, Official, BoxscoreTraditional

class BoxscoreTraditionalItem(DjangoItem):
	django_model = BoxscoreTraditional

class PlayerItem(DjangoItem):
	django_model = Player

	file_urls = scrapy.Field()
	files = scrapy.Field()

class TeamItem(DjangoItem):
	django_model = Team

	conference_name = scrapy.Field()
	division_name = scrapy.Field()
	
	file_urls = scrapy.Field()
	files = scrapy.Field()

class GameItem(DjangoItem):
	django_model = Game
	officials = scrapy.Field()

class OfficialItem(DjangoItem):
	django_model = Official

class CrappyItem(scrapy.Item):

    first_name = scrapy.Field()
    last_name = scrapy.Field()

class ArenaItem(scrapy.Item):

	name = scrapy.Field()
	capacity = scrapy.Field()
