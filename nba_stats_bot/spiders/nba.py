# -*- coding: utf-8 -*-
import scrapy
import json
import pprint
import dateutil.parser

from common.utils import iter_of_dicts_to_nested_dict, iter_of_list_to_iter_of_dicts, \
    iter_of_list_to_list_of_dicts, split_dict_to_iter_of_dicts, split_dict_to_list_of_dicts, \
    merge_dicts, datetime_count, current_season

from nba_stats_bot.items import PlayerItem, TeamItem, CrappyItem, ArenaItem, GameItem

from datetime import datetime, date, timedelta
from itertools import islice

# TODO: Extract magic constants and place
#       in common location

class GameSpider(scrapy.Spider):
    name = "games"
    allowed_domains = ["stats.nba.com"]

    def start_requests(self):
        kwargs = {
            'url': 'http://stats.nba.com/stats/scoreboardV2',
            'method': 'GET',
            'formdata': {
                'LeagueID': '00',
                'DayOffset': '0',
            },
            'callback': self.parse_game_list,
        }
        for d in islice(datetime_count(datetime.today(), timedelta(days=-1)), 20):
            print datetime.strftime(d, '%m/%d/%Y')
            kwargs['formdata']['GameDate'] = datetime.strftime(d, '%m/%d/%Y')
            yield scrapy.FormRequest(**kwargs)

    def parse_game_list(self, response):
        response_json = json.loads(response.body_as_unicode())
        norm_response_json = iter_of_dicts_to_nested_dict(response_json[u'resultSets'], u'name')
        for row in split_dict_to_iter_of_dicts(norm_response_json[u'GameHeader'], u'rowSet', u'headers'):
            yield GameItem(
                nba_id = row.get(u'GAME_ID'),
                nba_code = row.get(u'GAMECODE'),
                date = dateutil.parser.parse(row.get(u'GAME_DATE_EST')).date(),
                home = row.get(u'HOME_TEAM_ID'),
                away = row.get(u'VISITOR_TEAM_ID'),
                season = row.get(u'SEASON'),
            )
            yield scrapy.FormRequest(
                url = 'http://stats.nba.com/stats/boxscoresummaryv2',
                method = 'GET',
                formdata = {
                    'GameID': row.get(u'GAME_ID')
                },
                meta = {
                    'GameID': row.get(u'GAME_ID')
                },
                callback = self.parse_game_detail,
            )

    def parse_game_detail(self, response):
        response_json = json.loads(response.body_as_unicode())
        norm_response_json = iter_of_dicts_to_nested_dict(response_json[u'resultSets'], u'name')
        details_dict = next(split_dict_to_iter_of_dicts(norm_response_json[u'GameInfo'], u'rowSet', u'headers'))
        yield GameItem(
            nba_id = response.request.meta.get(u'GameID'),
            attendance = details_dict.get(u'ATTENDANCE'),
            duration = details_dict.get(u'GAME_TIME'),
        )

class TeamSpider(scrapy.Spider):
    name = "teams"
    allowed_domains = ["stats.nba.com"]

    def start_requests(self):
        kwargs = {
            'url': 'http://stats.nba.com/stats/commonTeamYears',
            'method': 'GET',
            'formdata': {
                'LeagueID': '00'
            },
            'callback': self.parse_team_list,
        }
        yield scrapy.FormRequest(**kwargs)

    def parse_team_list(self, response):
        response_json = json.loads(response.body_as_unicode())
        norm_response_json = iter_of_dicts_to_nested_dict(response_json[u'resultSets'], u'name')
        for row in split_dict_to_iter_of_dicts(norm_response_json[u'TeamYears'], u'rowSet', u'headers'):
            yield scrapy.FormRequest(
                url = 'http://stats.nba.com/stats/teaminfocommon',
                method = 'GET',
                callback = self.parse_team_detail_1,
                formdata = {
                    'TeamID': unicode(row.get(u'TEAM_ID')),
                    'LeagueID': '00',
                    'SeasonType': 'Regular Season',
                    'Season': current_season()
                }
            )
            yield scrapy.Request(
                url = 'http://stats.nba.com/feeds/teams/profile/{team_id}_TeamProfile.js' \
                    .format(team_id=unicode(row.get(u'TEAM_ID'))),
                callback = self.parse_team_detail_2,
            )

    def parse_team_detail_1(self, response):
        response_json = json.loads(response.body_as_unicode())
        norm_response_json = iter_of_dicts_to_nested_dict(response_json[u'resultSets'], u'name')
        details_dict = next(split_dict_to_iter_of_dicts(norm_response_json[u'TeamInfoCommon'], u'rowSet', u'headers'))
        yield TeamItem(
            nba_id = details_dict.get(u'TEAM_ID'),
            nba_code = details_dict.get(u'TEAM_CODE'),
            abbr = details_dict.get(u'TEAM_ABBREVIATION'),
            city = details_dict.get(u'TEAM_CITY'),
            nickname = details_dict.get(u'TEAM_NAME'),
            division_name = details_dict.get(u'TEAM_DIVISION'),
            conference_name = details_dict.get(u'TEAM_CONFERENCE'),
        )
        self.log(pprint.pformat(details_dict))

    def parse_team_detail_2(self, response):
        response_json = json.loads(response.body_as_unicode())
        norm_response_json = merge_dicts(*response_json[u'TeamDetails'])
        details_dict = norm_response_json[u'Details'][0]
        yield TeamItem(
            nba_id = details_dict.get(u'Team_Id'),
            abbr = details_dict.get(u'Abbreviation'),
            city = details_dict.get(u'City'),
            nickname = details_dict.get(u'Nickname'),
            file_urls = [
                'http://stats.nba.com/media/img/teams/logos/{Abbreviation}_logo.svg'.format(**details_dict)
            ],
            arena = ArenaItem(
                name = details_dict.get(u'Arena'),
                capacity = details_dict.get(u'ArenaCapacity'),
            )
        )
        # self.log(pprint.pformat(norm_response_json[u'Details']))

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
        results = iter_of_dicts_to_nested_dict(response_json[u'resultSets'], u'name')
        # We only expect one row from this so we use `next` to get the first one
        details_dict = next(split_dict_to_iter_of_dicts(results[u'CommonPlayerInfo'], u'rowSet', u'headers'))
        yield PlayerItem(
            nba_id = details_dict.get(u'PERSON_ID'),
            first_name = details_dict.get(u'FIRST_NAME'),
            last_name = details_dict.get(u'LAST_NAME'),
            # birth_date = dateutil.parser.parse(details_dict.get(u'BIRTHDATE')).date(),
            # school = details_dict.get(u'SCHOOL'),
            file_urls = [
                'http://stats.nba.com/media/players/230x185/{PERSON_ID}.png'.format(**details_dict),
                # 'http://stats.nba.com/media/players/170/{PERSON_ID}.png'.format(**details_dict)
            ],
        )
        # self.log(pprint.pformat(details_dict))

    def parse_player_detail_2(self, response):
        response_json = json.loads(response.body_as_unicode())
        results = merge_dicts(*response_json[u'PlayerProfile'])
        # self.log(pprint.pformat(results))
        details_dict = results[u'PlayerBio'][0]
        yield PlayerItem(
            nba_id = details_dict.get(u'Person_ID'),
            birth_date = dateutil.parser.parse(details_dict.get(u'Birthdate')).date(),
            school = details_dict.get(u'School'),
        )

    def parse_player_list(self, response):
        response_json = json.loads(response.body_as_unicode())
        results = iter_of_dicts_to_nested_dict(response_json[u'resultSets'], u'name')
        for row in split_dict_to_iter_of_dicts(results[u'CommonAllPlayers'], u'rowSet', u'headers'):
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
