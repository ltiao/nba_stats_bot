# -*- coding: utf-8 -*-
import scrapy
import json
import pprint

import common.utils

from nba_stats_bot.items import PlayerItem

class PlayerSpider(scrapy.Spider):
    name = "nba"
    allowed_domains = ["stats.nba.com"]

    def start_requests(self):
        kwargs = {
            'url': 'http://stats.nba.com/stats/commonallplayers',
            'method': 'GET',
            'formdata': {
                'LeagueID': '00', 
                'Season': common.utils.current_season(), 
                'IsOnlyCurrentSeason': '0'
            },
            'callback': self.parse_player_list
        }
        yield scrapy.FormRequest(**kwargs)

    def parse_player_detail_1(self, response):
        response_json = json.loads(response.body_as_unicode())
        results = common.utils.list_of_dicts_to_dict_of_dicts(response_json[u'resultSets'], u'name')
        # We only expect one row from this so we use `next` to get the first one
        details_dict = next(common.utils.split_dict_to_iter_of_dicts(results[u'CommonPlayerInfo'], u'rowSet', u'headers'))
        yield PlayerItem(
            nba_id = details_dict.get(u'PERSON_ID'),
            first_name = details_dict.get(u'FIRST_NAME'),
            last_name = details_dict.get(u'LAST_NAME'),
            birth_date = details_dict.get(u'BIRTHDATE'),
            school = details_dict.get(u'SCHOOL'),
        )
        # self.log(pprint.pformat(details_dict))

    def parse_player_detail_2(self, response):
        response_json = json.loads(response.body_as_unicode())
        results = common.utils.merge_dicts(*response_json[u'PlayerProfile'])
        details_dict = results[u'PlayerBio'][0]
        yield PlayerItem(
            nba_id = details_dict.get(u'Person_ID'),
            birth_date = details_dict.get(u'Birthdate'),
            school = details_dict.get(u'School'),
        )
        # self.log(pprint.pformat(details_dict))

    def parse_player_list(self, response):
        response_json = json.loads(response.body_as_unicode())
        results = common.utils.list_of_dicts_to_dict_of_dicts(response_json[u'resultSets'], u'name')
        for row in common.utils.split_dict_to_iter_of_dicts(results[u'CommonAllPlayers'], u'rowSet', u'headers'):
            yield scrapy.FormRequest(
                url = 'http://stats.nba.com/stats/commonplayerinfo',
                method = 'GET',
                callback = self.parse_player_detail_1,
                formdata = {
                    'PlayerID': unicode(row.get(u'PERSON_ID'))
                }
            )
            yield scrapy.FormRequest(
                url = 'http://stats.nba.com/feeds/players/profile/{player_id}_Profile.js' \
                    .format(
                        player_id=unicode(row.get(u'PERSON_ID'))
                    ),
                method = 'GET',
                callback = self.parse_player_detail_2,
            )


