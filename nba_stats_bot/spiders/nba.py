# -*- coding: utf-8 -*-
import scrapy
import json
import pprint
import dateutil.parser

import common.utils

from nba_stats_bot.items import PlayerItem, TeamItem, CrappyItem

# TODO: Extract magic constants and place
#       in common location

class TeamSpider(scrapy.Spider):
    name = "teams"
    allowed_domains = ["stats.nba.com"]

    def start_requests(self):
        kwargs = {
            'url': 'http://stats.nba.com/stats/commonTeamYears?LeagueID=00',
            'method': 'GET',
            'formdata': {
                'LeagueID': '00'
            },
            'callback': self.parse_team_list,
        }
        yield scrapy.FormRequest(**kwargs)

    def parse_team_list(self, response):
        response_json = json.loads(response.body_as_unicode())
        results = common.utils.list_of_dicts_to_dict_of_dicts(response_json[u'resultSets'], u'name')
        for row in common.utils.split_dict_to_iter_of_dicts(results[u'TeamYears'], u'rowSet', u'headers'):
            yield scrapy.Request(
                url = 'http://stats.nba.com/feeds/teams/profile/{team_id}_TeamProfile.js' \
                    .format(team_id=unicode(row.get(u'TEAM_ID'))),
                callback = self.parse_team_detail,
            )

    def parse_team_detail(self, response):
        response_json = json.loads(response.body_as_unicode())
        yield CrappyItem(first_name='Test')
        # self.log(pprint.pformat(response_json))

class PlayerSpider(scrapy.Spider):
    name = "players"
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
            'callback': self.parse_player_list,
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
            birth_date = dateutil.parser.parse(details_dict.get(u'BIRTHDATE')).date(),
            school = details_dict.get(u'SCHOOL'),
            # file_urls = [
            #     'http://stats.nba.com/media/players/230x185/{PERSON_ID}.png'.format(**details_dict),
            #     'http://stats.nba.com/media/players/170/{PERSON_ID}.png'.format(**details_dict)
            # ],
        )
        # self.log(pprint.pformat(details_dict))

    def parse_player_detail_2(self, response):
        response_json = json.loads(response.body_as_unicode())
        results = common.utils.merge_dicts(*response_json[u'PlayerProfile'])
        self.log(pprint.pformat(results))
        details_dict = results[u'PlayerBio'][0]
        yield PlayerItem(
            nba_id = details_dict.get(u'Person_ID'),
            birth_date = dateutil.parser.parse(details_dict.get(u'Birthdate')).date(),
            school = details_dict.get(u'School'),
        )

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
            yield scrapy.Request(
                url = 'http://stats.nba.com/feeds/players/profile/{player_id}_Profile.js' \
                    .format(
                        player_id=unicode(row.get(u'PERSON_ID'))
                    ),
                callback = self.parse_player_detail_2,
            )
