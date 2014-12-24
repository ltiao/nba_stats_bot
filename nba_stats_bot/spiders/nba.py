# -*- coding: utf-8 -*-
import scrapy


class PlayerSpider(scrapy.Spider):
    name = "nba"
    allowed_domains = ["stats.nba.com"]
    start_urls = (
        'http://www.nba.com/',
    )

    def parse(self, response):
        pass
