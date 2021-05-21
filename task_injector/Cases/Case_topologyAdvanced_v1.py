from Cases._RestdaCase import _RestdaCase
from Util.platform import *


class Case(_RestdaCase):
    def __init__(self):
        super(Case, self).__init__()
        self.Weight = 5
        self.ThinkTime = 3600 * 6

    def action(self):
        wait_for('Predefined_topologyAdvanced_v1', self.Weight)
        json_template = self.template('Predefined_topologyAdvanced_v1.json')
        json = json_template.substitute(dnContains='MRBTS-restda2000')
        token = RestdaAPI().read_token(self.CacheFile)
        self.flush_request_time()
        RestdaAPI().create_plan(token, json)
