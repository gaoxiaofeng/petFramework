from Cases._RestdaCase import _RestdaCase
from Util.platform import *


class Case(_RestdaCase):
    def __init__(self):
        super(Case, self).__init__()
        self.MaxCount = 1

    def action(self):
        json_template = self.template('Predefined_alarmDelta_v1_cron.json')
        token = RestdaAPI().read_token(self.CacheFile)
        json = json_template.substitute(duration='60', startTime=self.the_day_before(seconds=30),
                                        endTime=self.the_day_after(days=8), cronExpression="RESTDA_CRON 0 0 * * * ?")
        self.flush_request_time()
        RestdaAPI().create_plan(token, json)
