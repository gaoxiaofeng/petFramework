import collections
import json
import time
from os.path import isfile
from string import Template
import traceback
from Logger import Debug
from Variable import *


class _BaseCase(object):
    def __init__(self):
        super(_BaseCase, self).__init__()
        self.data = {}
        self.kwargs = {}
        self.caseId = self.__class__.__name__
        self.ThinkTime = None
        self.CacheFile = CASE_CACHE_FILE
        self.Counter = 0
        self.DateFormat = "%Y-%m-%dT%H:%M:%S"
        self.request_time = None
        self.Weight = 1
        self.MaxCount = 0

    def pre_action(self):
        pass

    def post_action(self):
        pass

    def action(self):
        pass

    def setattr(self, **kwargs):
        self.kwargs.update(kwargs)

    def do_pre_action(self):
        self.data.update({"caseId": self.caseId})
        self.pre_action()

    def do_action(self):
        try:
            self.Counter += 1
            self.request_time = time.time()
            self.data.update({"createTime": int(self.request_time)})
            self.action()
        except Exception as err:
            response_time = round(time.time() - self.request_time, 3)
            self.data.update({"ResponseTime": response_time, "status": FAIL, "error": str(err)})
            self.dump()
            raise Exception("Do action failed: {}. {}".format(err, traceback.format_exc()))
        else:
            response_time = round(time.time() - self.request_time, 3)
            self.data.update({"ResponseTime": response_time, "status": PASS})
            self.dump()

    def do_post_action(self):
        self.post_action()

    def flush_request_time(self):
        self.request_time = time.time()

    def dump(self):
        data_path = self.kwargs["dataPath"]
        if self.data["status"] == FAIL:
            data = collections.OrderedDict(caseId=self.data["caseId"],
                                           createTime=self.data["createTime"],
                                           ResponseTime=self.data["ResponseTime"],
                                           status=self.data["status"],
                                           error=self.data["error"])
        else:
            data = collections.OrderedDict(caseId=self.data["caseId"],
                                           createTime=self.data["createTime"],
                                           ResponseTime=self.data["ResponseTime"],
                                           status=self.data["status"])
        with open(data_path, "ab") as f:
            f.write("{}\n".format(json.dumps(data)).encode('utf-8'))

    @staticmethod
    def template(filename):
        if not filename.endswith(".json"):
            filename = "{}.json".format(filename)
        root_dir = dirname(dirname(abspath(__file__)))
        template_dir = join(root_dir, 'templates')
        template_path = join(template_dir, filename)
        if isfile(template_path):
            with open(template_path, 'rb') as f:
                content = f.read().decode('utf-8')
            return Template(content)
        else:
            error_message = 'Template file: {} is not exist.'.format(template_path)
            Debug.error(error_message)
            raise Exception(error_message)

    @staticmethod
    def constant(filename):
        root_dir = dirname(dirname(abspath(__file__)))
        template_dir = join(root_dir, 'templates')
        template_path = join(template_dir, filename)
        if isfile(template_path):
            with open(template_path, 'rb') as f:
                content = f.read().decode('utf-8')
            return content
        else:
            error_message = 'Template file: {} is not exist.'.format(template_path)
            Debug.error(error_message)
            raise Exception(error_message)
