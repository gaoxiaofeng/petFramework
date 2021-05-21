from Cases._RestdaCase import _RestdaCase
from Util.platform import *


class Case(_RestdaCase):
    def __init__(self):
        super(Case, self).__init__()
        # duration only support 15, 30, 60, 1440
        self.durations = [15, 30, 60, 1440]
        self.Weight = 2

    def action(self):
        duration = self.durations[self.Counter % len(self.durations)]
        workding_set_name = self.workingSets[self.Counter % len(self.workingSets)]
        wait_for('Predefined_alarmDelta_v1', self.Weight)
        json_template = self.template('Predefined_alarmDelta_v1.json')
        json = json_template.substitute(workingSetName=workding_set_name, duration=duration)
        token = RestdaAPI().read_token(self.CacheFile)
        self.flush_request_time()
        RestdaAPI().create_plan(token, json)
