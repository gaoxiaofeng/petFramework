from Cases._RestdaCase import _RestdaCase
from Util.platform import *


class Case(_RestdaCase):
    def __init__(self):
        super(Case, self).__init__()
        self.Weight = 1
        self.ThinkTime = 3600 * 6

    def action(self):
        wait_for('Predefined_topologyOfActiveAlarms_v2', self.Weight)
        # json = self.Constant('Predefined_topologyOfActiveAlarms_v2.json')
        json_template = self.template('Predefined_topologyOfActiveAlarms_v2.json')
        json = json_template.substitute(alarmNumberList='4001,4002,4003,4004,4005')
        token = RestdaAPI().read_token(self.CacheFile)
        self.flush_request_time()
        RestdaAPI().create_plan(token, json)
