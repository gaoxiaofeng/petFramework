import importlib
import os
from os.path import join, dirname, abspath

from Utility import singleton


@singleton
class ScenarioHandler(object):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.scenarioObjects = {}

    def scenario_init(self):
        scenarios_folder = join(dirname(abspath(__file__)), "Scenarios")
        for file_name in os.listdir(scenarios_folder):
            if not file_name.startswith("_") and file_name.endswith(".py"):
                class_name = "".join(file_name.split(".")[:-1])
                try:
                    module_object = importlib.import_module("Scenarios.{}".format(class_name))
                    self.scenarioObjects.update({class_name: module_object.Scenario()})
                except Exception as err:
                    raise Exception("failed to load file {} , because {}".format(file_name, err))

    @property
    def scenarios(self):
        return self.scenarioObjects

    @property
    def default_scenario_id(self):
        for scenarioId in self.scenarioObjects:
            return scenarioId

    @property
    def current_scenario_id(self):
        for scenarioId in self.scenarioObjects:
            if self.scenarioObjects[scenarioId].enable:
                return scenarioId
        return "unknow"

    def max_cases_count(self):
        max_cases_count = 0
        for scenarioId in self.scenarioObjects:
            scenario_object = self.scenarioObjects[scenarioId]
            if scenario_object.worker_count > max_cases_count:
                max_cases_count = scenario_object.worker_count
        return max_cases_count
