from Cases._RestdaCase import _RestdaCase
from Util.platform import *


class Case(_RestdaCase):
    def __init__(self):
        super(Case, self).__init__()
        self.ThinkTime = 30
        self.duration = [12, 24]
        # duration is unlimited
        self.Weight = 3

    def action(self):
        adaptation_measurement = self.measurements_sbts[self.Counter % len(self.measurements_sbts)]
        workingset_name = "SBTS"
        duration = self.duration[self.Counter % len(self.duration)]
        adaptation = adaptation_measurement[0]
        measurements = adaptation_measurement[1]
        wait_for('Predefined_performanceData_v1', self.Weight)
        json_template = self.template('Predefined_performanceData_v1.json')
        offset_time = 2
        json = json_template.substitute(adaptationid=adaptation, measurementTypeList=measurements,
                                        workingsetName=workingset_name,
                                        dataStartTime=self.the_day_before(hours=duration + offset_time),
                                        dataEndTime=self.the_day_before(hours=offset_time))
        token = RestdaAPI().read_token(self.CacheFile)
        self.flush_request_time()
        RestdaAPI().create_plan(token, json)
