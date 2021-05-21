from Cases._RestdaCase import _RestdaCase
from Util.platform import *


class Case(_RestdaCase):
    def __init__(self):
        super(Case, self).__init__()
        self.duration = [1, 6, 12, 24, 48]
        # only 1 million alarms be record to result file
        self.Weight = 1

    def action(self):
        duration = self.duration[self.Counter % len(self.duration)]
        wait_for('Predefined_historyFMAlarms_v1', self.Weight)
        json_template = self.template('Predefined_historyFMAlarms_v1.json')
        json = json_template.substitute(dataStartTime=self.the_day_before(hours=duration),
                                        dataEndTime=self.the_day_now())
        token = RestdaAPI().read_token(self.CacheFile)
        self.flush_request_time()
        RestdaAPI().create_plan(token, json)
