from Cases._RestdaCase import _RestdaCase
from Util.platform import *


class Case(_RestdaCase):
    def __init__(self):
        super(Case, self).__init__()
        self.Weight = 5
        self.ThinkTime = 3600 * 3

    def action(self):
        workding_set_name = self.workingSets[self.Counter % len(self.workingSets)]
        wait_for('Predefined_activeAlarms_v3', self.Weight)
        json_template = self.template('Predefined_activeAlarms_v3.json')
        json = json_template.substitute(workingSetName=workding_set_name, includeDescendants='True',
                                        dataStartTime=self.the_day_before(days=7),
                                        dataEndTime=self.the_day_after(minutes=5))
        token = RestdaAPI().read_token(self.CacheFile)
        self.flush_request_time()
        RestdaAPI().create_plan(token, json)
