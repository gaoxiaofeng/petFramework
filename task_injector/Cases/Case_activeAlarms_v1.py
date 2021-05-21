from Cases._RestdaCase import _RestdaCase
from Util.platform import *


class Case(_RestdaCase):
    def __init__(self):
        super(Case, self).__init__()
        self.Weight = 5
        self.ThinkTime = 3600 * 3

    def action(self):
        workding_set_name = self.workingSets[self.Counter % len(self.workingSets)]
        wait_for('Predefined_activeAlarms_v1', self.Weight)
        json_template = self.template('Predefined_activeAlarms_v1.json')
        json = json_template.substitute(dataStartTime=self.the_day_before(days=2),
                                        dataEndTime=self.the_day_after(minutes=5),
                                        dnContains='PLMN-PLMN', workingsetName=workding_set_name)
        token = RestdaAPI().read_token(self.CacheFile)
        self.flush_request_time()
        RestdaAPI().create_plan(token, json)
