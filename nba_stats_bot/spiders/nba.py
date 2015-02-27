# -*- coding: utf-8 -*-
import scrapy
import json
import pprint
import functools
import dateutil.parser

from common.utils import iter_of_dicts_to_nested_dict, iter_of_list_to_iter_of_dicts, \
    iter_of_list_to_list_of_dicts, split_dict_to_iter_of_dicts, split_dict_to_list_of_dicts, \
    merge_dicts, datetime_count, current_season

from nba_stats_bot.items import PlayerItem, TeamItem, CrappyItem, ArenaItem, GameItem, OfficialItem, BoxscoreTraditionalItem

from datetime import datetime, date, timedelta
from itertools import islice

# TODO: Extract magic constants and place
#       in common location

def response_json(parse_method):

    @functools.wraps(parse_method)
    def wrapper(self, response):

        self.log('Parsing raw text response to json...')

        response_json = json.loads(response.body_as_unicode())

        return parse_method(self, response, response_json)

    return wrapper

def norm_response_json(k1, k2):
    def norm_response_json_decorator(parse_method):
        @functools.wraps(parse_method)
        @response_json
        def wrapper(self, response, response_json):
            self.log('Parsing raw text response to json...')
            return parse_method(self, response, iter_of_dicts_to_nested_dict(response_json[k1], k2))
        return wrapper
    return norm_response_json_decorator

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

    @norm_response_json(u'resultSets', u'name')
    def parse_game_list(self, response, response_json):
        for row in split_dict_to_iter_of_dicts(response_json[u'GameHeader'], u'rowSet', u'headers'):
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
            yield scrapy.FormRequest(
                url = 'http://stats.nba.com/stats/boxscoretraditionalv2',
                method = 'GET',
                formdata = {
                    'GameID': row.get(u'GAME_ID'),
                    'RangeType': unicode(2),
                    'StartPeriod': unicode(1),
                    'EndPeriod': unicode(10),
                    'StartRange': unicode(0),
                    'EndRange': unicode(48 * 60 * 10) # 48 minutes in deciseconds
                },
                callback = self.parse_game_boxscore,
            )

    @norm_response_json(u'resultSets', u'name')
    def parse_game_boxscore(self, response, response_json):
        for boxscore_dict in split_dict_to_iter_of_dicts(response_json[u'PlayerStats'], u'rowSet', u'headers'):
            yield BoxscoreTraditionalItem(
                game = boxscore_dict.get(u'GAME_ID'),
                player = boxscore_dict.get(u'PLAYER_ID'),
                team = boxscore_dict.get(u'TEAM_ID'),
                pts = boxscore_dict.get(u'PTS'),
                ast = boxscore_dict.get(u'AST'),
                reb = boxscore_dict.get(u'REB'),
            )
            self.log(pprint.pformat(boxscore_dict))

    @norm_response_json(u'resultSets', u'name')
    def parse_game_detail(self, response, response_json):
        details_dict = next(split_dict_to_iter_of_dicts(response_json[u'GameInfo'], u'rowSet', u'headers'))
        yield GameItem(
            nba_id = response.request.meta.get(u'GameID'),
            attendance = details_dict.get(u'ATTENDANCE'),
            duration = details_dict.get(u'GAME_TIME'),
            officials = [OfficialItem(
                nba_id = row.get(u'OFFICIAL_ID'),
                first_name = row.get(u'FIRST_NAME'),
                last_name = row.get(u'LAST_NAME'),
                jersey_num = int(row.get(u'JERSEY_NUM').rstrip()),
            ) for row in split_dict_to_iter_of_dicts(response_json[u'Officials'], u'rowSet', u'headers')]
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

    @norm_response_json(u'resultSets', u'name')
    def parse_team_list(self, response, response_json):
        for row in split_dict_to_iter_of_dicts(response_json[u'TeamYears'], u'rowSet', u'headers'):
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

    @norm_response_json(u'resultSets', u'name')
    def parse_team_detail_1(self, response, response_json):
        details_dict = next(split_dict_to_iter_of_dicts(response_json[u'TeamInfoCommon'], u'rowSet', u'headers'))
        yield TeamItem(
            nba_id = details_dict.get(u'TEAM_ID'),
            nba_code = details_dict.get(u'TEAM_CODE'),
            abbr = details_dict.get(u'TEAM_ABBREVIATION'),
            city = details_dict.get(u'TEAM_CITY'),
            nickname = details_dict.get(u'TEAM_NAME'),
            division_name = details_dict.get(u'TEAM_DIVISION'),
            conference_name = details_dict.get(u'TEAM_CONFERENCE'),
        )
        # self.log(pprint.pformat(details_dict))

    @response_json
    def parse_team_detail_2(self, response, response_json):
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
                'Season': current_season(), 
                'IsOnlyCurrentSeason': '0'
            },
            'callback': self.parse_player_list,
        }
        yield scrapy.FormRequest(**kwargs)

    @norm_response_json(u'resultSets', u'name')
    def parse_player_detail_1(self, response, response_json):
        # We only expect one row from this so we use `next` to get the first one
        details_dict = next(split_dict_to_iter_of_dicts(response_json[u'CommonPlayerInfo'], u'rowSet', u'headers'))
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

    @response_json
    def parse_player_detail_2(self, response, response_json):
        results = merge_dicts(*response_json[u'PlayerProfile'])
        # self.log(pprint.pformat(results))
        details_dict = results[u'PlayerBio'][0]
        yield PlayerItem(
            nba_id = details_dict.get(u'Person_ID'),
            birth_date = dateutil.parser.parse(details_dict.get(u'Birthdate')).date(),
            school = details_dict.get(u'School'),
        )

    @norm_response_json(u'resultSets', u'name')
    def parse_player_list(self, response, response_json):
        for row in split_dict_to_iter_of_dicts(response_json[u'CommonAllPlayers'], u'rowSet', u'headers'):
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
