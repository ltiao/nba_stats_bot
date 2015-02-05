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
from nba.models import Player, School, Team, Arena, Division, Conference, Group
from nba_stats_bot.settings import FILES_STORE

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

class UnhashedFilesPipeline(FilesPipeline):

    def file_path(self, request, response=None, info=None):
        super(UnhashedFilesPipeline, self).file_path(request, response, info)      
        return 'full/{}'.format(request.url.split('/')[-1])

class TeamPipeline:

    spiders = ['teams']

    @selective
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


        # try:
        #     division_dict = item_dict['division']
            
        #     try:
        #         conference_dict = division_dict['conference']
        #         conference_obj, _ = Conference.objects.get_or_create(
        #             name = conference_dict.get('name'), 
        #             defaults = conference_dict
        #         ) 
        #         division_dict['conference'] = conference_obj
        #     except KeyError:
        #         division_dict['conference'] = None

        #     division_obj, _ = Division.objects.update_or_create(
        #         name = division_dict.get('name'), 
        #         defaults = division_dict
        #     )

        #     item_dict['division'] = division_obj
        # except KeyError:
        #     pass

        file_urls = item_dict.pop('file_urls', None)
        files_dicts = item_dict.pop('files', [])

        print item_dict

        team_obj, _ = Team.objects.update_or_create(nba_id=item_dict.get('nba_id'), defaults=item_dict)
        
        for file_dict in files_dicts:
            with open(os.path.join(FILES_STORE, file_dict.get('path'))) as f:
                team_obj.logo.save(os.path.basename(file_dict.get('path')), File(f))
        
        return item

class PlayerPipeline:

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

        file_urls = item_dict.pop('file_urls', None)
        files_dicts = item_dict.pop('files', [])

        player_obj, _ = Player.objects.update_or_create(nba_id=item_dict.get('nba_id'), defaults=item_dict)
        
        for file_dict in files_dicts:
            with open(os.path.join(FILES_STORE, file_dict.get('path'))) as f:
                player_obj.photo.save(os.path.basename(file_dict.get('path')), File(f))

        return item
