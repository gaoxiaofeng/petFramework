from Cases._RestdaCase import _RestdaCase
from Util.platform import *


class Case(_RestdaCase):
    def __init__(self):
        super(Case, self).__init__()
        self.ThinkTime = 3
        self.duration = [1, 2, 3]
        # duration is unlimited
        self.Weight = 3
        self.RestdaSleepTime = 10

    def action(self):
        wait_until("Predefined_performanceData_v1")
        time.sleep(self.RestdaSleepTime)
        adaptation_measurement = self.measurements_sbts[self.Counter % len(self.measurements_sbts)]
        workingset_name = "SBTS"
        adaptation = adaptation_measurement[0]
        measurements = adaptation_measurement[1]
        json_template = self.template('Predefined_performanceData_v1')
        offset_time = 2
        token = RestdaAPI().read_token(self.CacheFile)
        self.flush_request_time()
        for i in range(self.Weight):
            duration = self.duration[i]
            json = json_template.substitute(adaptationid=adaptation, measurementTypeList=measurements,
                                            workingsetName=workingset_name,
                                            dataStartTime=self.the_day_before(hours=duration + offset_time),
                                            dataEndTime=self.the_day_before(hours=offset_time))
            RestdaAPI().create_plan(token, json)
