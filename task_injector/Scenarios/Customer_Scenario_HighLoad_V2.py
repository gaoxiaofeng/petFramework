from Scenarios._BaseScenario import _BaseScenario


class Scenario(_BaseScenario):
    def __init__(self):
        super(Scenario, self).__init__()
        query_cases = [
            "Case_Issue_Token",
        ]

        fm_cases = [
            "Case_alarmDelta_v1_batch_15min",
            "Case_alarmDelta_v1_batch_30min",
            "Case_alarmDelta_v1_batch_60min",
            "Case_alarmDelta_v1_batch_1440min",
            "Case_fm_mixed",
        ]

        pm_cases = [
            "Case_pm_mixed",
        ]

        self.WorkerCases = fm_cases + pm_cases + query_cases
        self.Duration = 7 * 24 * 60 * 60
        self.DefaultThinkTime = 5
        self.ForceThinkTime = 3
