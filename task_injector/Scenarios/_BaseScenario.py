from CaseHandler import CaseHandler


class _BaseScenario(object):
    def __init__(self):
        super(_BaseScenario, self).__init__()
        self.kwargs = {}
        self.scenarioId = self.__class__.__name__
        self.CaseHandler = CaseHandler()
        # customer configure
        self.Duration = 3600
        self.DefaultThinkTime = None
        self.ForceThinkTime = None
        self.WorkerCases = [
            self.CaseHandler.default_case_id,
            self.CaseHandler.default_case_id,
            self.CaseHandler.default_case_id,
            self.CaseHandler.default_case_id,
        ]
        self.enable = False
        self.AnalysisMode = {
            "AverageResponseTime": True,
            "MaximumResponseTime": True,
            "MinimumResponseTime": True,
            "PassTaskCount": True,
            "FailTaskCount": True,
        }

    @property
    def worker_count(self):
        return len(self.WorkerCases)
