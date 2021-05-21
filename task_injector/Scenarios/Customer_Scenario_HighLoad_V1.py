from Scenarios._BaseScenario import _BaseScenario


class Scenario(_BaseScenario):
    def __init__(self):
        super(Scenario, self).__init__()
        query_cases = [
            "Case_Issue_Token",
            # "Case_Query_Plans",
            # "Case_Query_Templates",
            # "Case_Query_Tasks"
        ]

        fm_withw_set_cases = [
            "Case_activeAlarms_v1",
            "Case_activeAlarms_v2",
            "Case_activeAlarms_v3",
            "Case_alarmDelta_v1_batch_15min",
            "Case_alarmDelta_v1_batch_30min",
            "Case_alarmDelta_v1_batch_60min",
            "Case_alarmDelta_v1_batch_1440min",

        ]

        fm_without_wset_cases = [
            "Case_topologyAdvanced_v1",
            "Case_topologyOfActiveAlarms_v1",
            "Case_topologyOfActiveAlarms_v2",
        ]

        pm_instant_cases = [
            "Case_performanceData_v1_noklte_standard",
        ]

        self.WorkerCases = fm_withw_set_cases + fm_without_wset_cases + pm_instant_cases + query_cases
        self.Duration = 7 * 24 * 60 * 60
        self.DefaultThinkTime = 30
        self.ForceThinkTime = 30
