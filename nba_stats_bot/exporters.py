from scrapy.conf import settings
from scrapy.contrib.exporter import JsonItemExporter

class DjangoFixtureExporter(JsonItemExporter):

    def export_item(self, item):
        
        if self.first_item:
            self.first_item = False
        else:
            self.file.write(',\n')
        
        itemdict = {
            'fields': dict(self._get_serialized_fields(item)),
            'model': 'nba.player'
        }
        
        self.file.write(self.encoder.encode(itemdict))