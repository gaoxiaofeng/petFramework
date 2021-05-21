import importlib
import os
from os.path import join, dirname, abspath

from Utility import singleton


@singleton
class CaseHandler(object):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.caseObjects = {}

    def case_init(self):
        cases_folder = join(dirname(abspath(__file__)), "Cases")
        for fileName in os.listdir(cases_folder):
            if not fileName.startswith("_") and fileName.endswith(".py"):
                class_name = "".join(fileName.split(".")[:-1])
                try:
                    module_object = importlib.import_module("Cases.{}".format(class_name))
                    self.caseObjects.update({class_name: module_object.Case()})
                except Exception as err:
                    raise Exception("failed to load file {} , because {}".format(fileName, err))

    @property
    def cases(self):
        return self.caseObjects

    @property
    def default_case_id(self):
        for caseId in self.caseObjects:
            return caseId
