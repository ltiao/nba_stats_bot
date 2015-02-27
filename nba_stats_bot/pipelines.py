# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import functools
import django
import os

django.setup()

from scrapy import log
from scrapy.contrib.pipeline.files import FilesPipeline

from django.core.files import File
from nba.models import Player, School, Team, Arena, Division, Conference, Group, Game, Season, Official, BoxscoreTraditional
from nba_stats_bot.settings import FILES_STORE
from pprint import pprint, pformat

def filter_spiders(*spiders):
    
    def filter_spiders_decorator(process_item_method):
    
        @functools.wraps(process_item_method)
        def wrapper(self, item, spider):
            msg = '{{}} {} pipeline step: "{}" {{}}in {}' \
                .format(self.__class__.__name__, spider.name, spiders)

            if spider.name in spiders:
                spider.log(msg.format('Executing', ''), level=log.DEBUG)
                item = process_item_method(self, item, spider)
            else:
                spider.log(msg.format('Skipping', 'not '), level=log.DEBUG)
            
            return item
        
        return wrapper

    return filter_spiders_decorator

def filter_items(*items):
    
    def filter_items_decorator(process_item_method):
    
        @functools.wraps(process_item_method)
        def wrapper(self, item, spider):
            msg = '{{}} {} pipeline step: "{}" {{}}in {}' \
                .format(self.__class__.__name__, item.__class__.__name__, items)

            if item.__class__.__name__ in items:
                spider.log(msg.format('Executing', ''), level=log.DEBUG)
                item = process_item_method(self, item, spider)
            else:
                spider.log(msg.format('Skipping', 'not '), level=log.DEBUG)
            
            return item
        
        return wrapper

    return filter_items_decorator

class UnhashedFilesPipeline(FilesPipeline):

    def file_path(self, request, response=None, info=None):
        super(UnhashedFilesPipeline, self).file_path(request, response, info)      
        return 'full/{}'.format(request.url.split('/')[-1])

class MultiItemPipeline:

    def process_item(self, item, spider):
        spider.log('Item of type {0}'.format(item.__class__.__name__), level=log.DEBUG)
        item_callback = self.item_callbacks.get(item.__class__.__name__)
        if callable(item_callback):
            return item_callback(item, spider)
        else:
            spider.log('Callback for item of type {0} is not callable'.format(item.__class__.__name__), level=log.ERROR)
            return item

class GamePipeline(MultiItemPipeline):

    def __init__(self):
        self.item_callbacks = {
            'GameItem': self.process_game_item,
            'BoxscoreTraditionalItem': self.process_boxscore_item,
        }

    @filter_spiders('games')
    def process_boxscore_item(self, item, spider):
        
        spider.log('processing boxscore!!!', level=log.DEBUG)  

        item_dict = dict(item)

        item_dict['team'] = Team.objects.get(nba_id=item_dict['team'])
        item_dict['player'] = Player.objects.get(nba_id=item_dict['player'])
        item_dict['game'] = Game.objects.get(nba_id=item_dict['game'])

        BoxscoreTraditional.objects.update_or_create(**item_dict)

        return item

    @filter_spiders('games')
    def process_game_item(self, item, spider):

        item_dict = dict(item)
        
        try:
            item_dict['officials'] = [
                Official.objects.get_or_create(nba_id=official.get('nba_id'), defaults=official)[0] 
                for official in item_dict['officials']
            ]
        except KeyError:
            spider.log('officials data not present', level=log.DEBUG)  

        try:
            item_dict['home'] = Team.objects.get(nba_id=item_dict['home'])
            item_dict['away'] = Team.objects.get(nba_id=item_dict['away'])
        except KeyError:
            spider.log('paricipating team data not present', level=log.DEBUG)

        try:
            item_dict['duration'] = sum(a*b for a, b in zip((60, 1), map(int, item_dict['duration'].split(':'))))
        except:
            spider.log('duration data not present', level=log.DEBUG)

        try:
            season_obj, _ = Season.objects.update_or_create(start_year=int(item_dict['season']))
            item_dict['season'] = season_obj
        except KeyError:
            spider.log('season data not present', level=log.DEBUG)

        game_obj, _ = Game.objects.update_or_create(nba_id=item_dict.get('nba_id'), defaults=item_dict)

        return item

class TeamPipeline:

    @filter_spiders('teams')
    def process_item(self, item, spider):
        item_dict = dict(item)

        try:
            arena_dict = item_dict['arena']
            arena_obj, _ = Arena.objects.update_or_create(name=arena_dict.get('name'), defaults=arena_dict)
            item_dict['arena'] = arena_obj
        except KeyError:
            spider.log('arena data not present', level=log.DEBUG)

        try:
            conference_name = item_dict.pop('conference_name')
            conference_obj, _ = Conference.objects.get_or_create(name=conference_name)
        except KeyError:
            spider.log('conference data not present', level=log.DEBUG)
            conference_obj = None

        try:
            division_name = item_dict.pop('division_name')
            division_obj, _ = Division.objects.update_or_create(
                name = division_name, 
                parent = conference_obj,
            )
            item_dict['division'] = division_obj
        except KeyError:
            spider.log('division data not present', level=log.DEBUG)

        file_urls = item_dict.pop('file_urls', None)
        files_dicts = item_dict.pop('files', [])

        print item_dict

        team_obj, _ = Team.objects.update_or_create(nba_id=item_dict.get('nba_id'), defaults=item_dict)
        
        for file_dict in files_dicts:
            with open(os.path.join(FILES_STORE, file_dict.get('path'))) as f:
                team_obj.logo.save(os.path.basename(file_dict.get('path')), File(f))
        
        return item

class PlayerPipeline:

    def __init__(self):
        pass

    def open_spider(self, spider):
        pass

    def close_spider(self, spider):
        pass

    @filter_spiders('players')
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

        file_urls = item_dict.pop('file_urls', None)
        files_dicts = item_dict.pop('files', [])

        player_obj, _ = Player.objects.update_or_create(nba_id=item_dict.get('nba_id'), defaults=item_dict)
        
        for file_dict in files_dicts:
            with open(os.path.join(FILES_STORE, file_dict.get('path'))) as f:
                player_obj.photo.save(os.path.basename(file_dict.get('path')), File(f))

        return item
