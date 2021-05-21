import random

from Cases._RestdaCase import _RestdaCase
from Util.platform import *


class Case(_RestdaCase):
    def __init__(self):
        super(Case, self).__init__()
        self.Weight = 3
        self.ThinkTime = 3
        self.templateIds = ["Predefined_activeAlarms_v1",
                            "Predefined_activeAlarms_v2",
                            "Predefined_activeAlarms_v3",
                            "Predefined_topologyOfActiveAlarms_v1",
                            "Predefined_topologyOfActiveAlarms_v2",
                            "Predefined_topologyAdvanced_v1"]
        self.RestdaSleepTime = 10

    def action(self):
        wait_until(*self.templateIds)
        time.sleep(self.RestdaSleepTime)
        template_ids = [random.choice(self.templateIds) for i in range(self.Weight)]
        workding_set_name = self.workingSets[self.Counter % len(self.workingSets)]
        token = RestdaAPI().read_token(self.CacheFile)
        self.flush_request_time()
        for templateId in template_ids:
            json_template = self.template(templateId)
            if templateId in ("Predefined_activeAlarms_v1", "Predefined_activeAlarms_v2"):
                json = json_template.substitute(dataStartTime=self.the_day_before(days=7),
                                                dataEndTime=self.the_day_after(minutes=5), dnContains='PLMN-PLMN',
                                                workingsetName=workding_set_name)
            elif templateId == "Predefined_activeAlarms_v3":
                json = json_template.substitute(workingSetName=workding_set_name, includeDescendants='True',
                                                dataStartTime=self.the_day_before(days=7),
                                                dataEndTime=self.the_day_after(minutes=5))
            elif templateId == "Predefined_topologyAdvanced_v1":
                json = json_template.substitute(dnContains='MRBTS-restda2000')
            elif templateId == "Predefined_topologyOfActiveAlarms_v1":
                json = json_template.substitute(alarmNumberList='4001', objectClassList="BSC")
            elif templateId == "Predefined_topologyOfActiveAlarms_v2":
                json = json_template.substitute(alarmNumberList='4001,4002,4003,4004,4005')
            else:
                raise Exception("unknown template Id")
            RestdaAPI().create_plan(token, json)
