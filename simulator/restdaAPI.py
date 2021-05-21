#!/usr/bin/env python
import json
import logging
import optparse
import os
import re
import subprocess
import sys
import time

DEBUG = None
IGNORE = None

RESTDA_CUSTOMER_PROPERTIES_PATH = "/etc/opt/oss/global/restda/conf/restda_customer.properties"
RESTDA_FRONTEND_INTERNAL_PROPERTIES_PATH = "/opt/oss/restda/conf/restda_internal.properties"
RESTDA_COMMON_INTERNAL_PROPERTIES_PATH = "/opt/oss/Nokia-restda-common/conf/restda-common.properties"
RESTDA_FM_INTERNAL_PROPERTIES_PATH = "/opt/oss/Nokia-restda-fm/conf/restda_internal.properties"
RESTDA_PM_INTERNAL_PROPERTIES_PATH = "/opt/oss/Nokia-restda-pm/conf/restda_pm.properties"
ENABLE_STARTUP_ITEM = "com.nokia.oss.restda.startup.enable"
ENABLE_PM_ITEM = "com.nokia.oss.restda.pm.is.enable"
ENABLE_FM_ITEM = "com.nokia.oss.restda.fm.is.enable"


class Logger(object):
    logger = logging.getLogger("Logger")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s: %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    @classmethod
    def info(cls, message):
        message = message.strip()
        cls.logger.info(message)

    @classmethod
    def error(cls, message):
        message = message.strip()
        cls.logger.error(message)

    @classmethod
    def debug(cls, message):
        message = message.strip()
        cls.logger.debug(message)

    @classmethod
    def warning(cls, message):
        message = message.strip()
        cls.logger.warning(message)

    @classmethod
    def enable_debug(cls):
        cls.logger.setLevel(logging.DEBUG)


def execute_command(command):
    global DEBUG
    command = command.strip()
    if DEBUG:
        print("-" * 100)
        print("command:", command)
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    stdout = stdout.decode('utf-8').strip()
    stderr = stderr.decode('utf-8').strip()
    rc = process.returncode
    if DEBUG:
        print("stdout:", stdout)
        print("stderr:", stderr)
        print("rc:", rc)
        print("-" * 100)
    return stdout, stderr, rc


def remote_execute_command(host, command):
    remote_command = "ssh root@{host_name} {commands}".format(host_name=host, commands=command)
    return execute_command(remote_command)


class Sed(object):
    def __init__(self):
        super(Sed, self).__init__()

    @staticmethod
    def _execute(command):
        stdout, stderr, rc = execute_command(command)
        assert rc == 0, stderr
        return stdout

    @classmethod
    def set(cls, configfile, key, value):
        command = r"sed -i --follow-symlinks 's/\s*%s\s*=.*/%s=%s/g' %s" % (key, key, value, configfile)
        cls._execute(command)

    @classmethod
    def remote_set(cls, host, configfile, key, value):
        command = r"ssh root@{host} sed -i --follow-symlinks 's/\s*{key}\s*=.*/{key}={value}/g' {configfile}".format(
            host=host, key=key, value=value, configfile=configfile)
        cls._execute(command)

    @classmethod
    def get(cls, configfile, key):
        command = r"sed -n '/%s/p' %s" % (key, configfile)
        content = cls._execute(command)
        if content and "=" in content and content[content.index("=") + 1:].strip() == "true":
            return "true"
        else:
            return "false"

    @classmethod
    def remote_get(cls, host, configfile, key):
        command = "ssh root@%s sed -n '/%s/p' %s" % (host, key, configfile)
        content = cls._execute(command)
        if content and "=" in content and content[content.index("=") + 1:].strip() == "true":
            return "true"
        else:
            return "false"


class Curl(object):
    @staticmethod
    def _excute(command, *args):
        command = command.strip()
        command += " " + " ".join(args)
        stdout, stderr, rc = execute_command(command)
        assert rc == 0, stderr
        return stdout

    @staticmethod
    def _format_result(content):
        content = json.loads(content)
        if "errorCode" in content:
            print(json.dumps(content, indent=4))
            if not IGNORE:
                sys.exit(1)
        return content

    @classmethod
    def post(cls, url, *args):
        command = """
        curl -v -k -X "POST"  "{}"
        """.format(url)
        content = cls._excute(command, *args)
        return cls._format_result(content)

    @classmethod
    def get(cls, url, *args):
        command = """
        curl -v -k -X "GET"  "{}"
        """.format(url)
        content = cls._excute(command, *args)
        return cls._format_result(content)

    @classmethod
    def download(cls, url, *args):
        command = """
        curl -D - -k -X "GET"  "{}" -O 
        """.format(url)
        content = cls._excute(command, *args)
        expression = r'.*?filename="(.+?)"'
        pattern = re.compile(expression, re.M | re.S)
        match = pattern.match(content)
        if match:
            filename = match.group(1)
            temp_filename = url.split("/")[-1]
            command = "mv {} {}".format(temp_filename, filename)
            cls._excute(command)
            return "download file {} success".format(filename)
        else:
            print("failed to download result file {}".format(url))
            sys.exit(1)

    @classmethod
    def delete(cls, url, *args):
        command = """
        curl -v -k -X "DELETE"  "{}"
        """.format(url)
        content = cls._excute(command, *args)
        return cls._format_result(content)


class CreatePlanAgreement(object):
    _cron = dict(name="create cron Plan",
                 description="create cron Plan by {}".format(__file__),
                 startTime="2018-01-01T10:00:00",
                 endTime="2099-01-01T10:00:00",
                 cronExpression="RESTDA_CRON 0/15 * * * * ?")
    _oneTime = dict(name="create One Time Plan",
                    description="create One Time Plan by {}".format(__file__), )
    _future = dict(name="create future Plan",
                   description="create future Plan by {}".format(__file__),
                   startTime="2099-01-01T10:00:00")
    typeMap = dict(cron=_cron, oneTime=_oneTime, future=_future)
    typeList = list(typeMap.keys())

    @classmethod
    def predefined_template(cls, template_id, type_name):
        assert type_name in cls.typeMap, "type invalid."
        template_content = cls.typeMap[type_name]
        template_content.update(dict(templateId=template_id))
        if template_id == "Predefined_performanceData_v1":
            now = time.time()
            current_date = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(now))
            yesterday_date = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(now - 60 * 60 * 24))
            argument_list = [
                dict(
                    adaptationId="noklte",
                    startTime=yesterday_date,
                    endTime=current_date
                )
            ]
        elif template_id in ["Predefined_topologyOfActiveAlarms_v1",
                             "Predefined_topologyOfActiveAlarms_v2"]:
            argument_list = [
                dict(
                    ObjectNameContains="PLMN-PLMN",
                )
            ]
        elif template_id in ["Predefined_topologyAdvanced_v1"]:
            argument_list = [
                dict(
                    ObjectNameContains="PLMN-PLMN",
                )
            ]
        elif template_id in ["Predefined_activeAlarms_v1",
                             "Predefined_activeAlarms_v2",
                             "Predefined_activeAlarms_v3"]:
            argument_list = [
                dict(
                    dnContains="PLMN-PLMN",
                )
            ]
        elif template_id in ["Predefined_historyFMAlarms_v1"]:
            argument_list = [
                dict(
                    dnContains="PLMN-PLMN",
                )
            ]
        elif template_id in ["Predefined_alarmDelta_v1"]:
            argument_list = [
                dict(
                    duration="15",
                )
            ]
        template_content.update(dict(argumentList=argument_list))
        return template_content


class BashHandle(object):
    def __init__(self):
        super(BashHandle, self).__init__()
        self.successor = None

    @staticmethod
    def _execute(command):
        stdout, stderr, rc = execute_command(command)
        assert rc == 0, "err: {}".format(stdout + stderr)
        return stdout

    def handle(self, **kwargs):
        if self.successor:
            self.successor.handle(**kwargs)


class GetPassword(BashHandle):
    def __init__(self):
        super(GetPassword, self).__init__()

    def fetch_password(self, user):
        command = "/opt/nokia/oss/bin/syscredacc.sh -user {} -type appserv -instance appserv".format(user)
        try:
            password = self._execute(command)
        except Exception as err:
            print("failed to fetch password for {} , reason: {}".format(user, err))
            sys.exit(1)
        return password

    def handle(self, **kwargs):
        if not any([kwargs["password"], kwargs["token"]]):
            password = self.fetch_password(kwargs["user"])
            kwargs.update(dict(password=password))
        super(GetPassword, self).handle(**kwargs)


class GetLBWAS(BashHandle):
    def __init__(self):
        super(GetLBWAS, self).__init__()

    def fetch_load_balance(self):
        command = "/opt/cpf/bin/cpf_list_lb_address.sh --lb was"
        try:
            fqdn = self._execute(command)
        except Exception as err:
            print("failed to get fqdn , reason: {}".format(err))
            sys.exit(1)
        return fqdn

    def handle(self, **kwargs):
        if "lbwas" in kwargs and kwargs["lbwas"]:
            kwargs.update(dict(fqdn=kwargs["lbwas"]))
        else:
            fqdn = self.fetch_load_balance()
            kwargs.update(dict(fqdn=fqdn))
        super(GetLBWAS, self).handle(**kwargs)


class SearchService(BashHandle):
    def __init__(self):
        super(SearchService, self).__init__()

    @classmethod
    def _get_service_node_and_status_by_smanager(cls, service):
        try:
            result = cls._execute("smanager.pl status service ^{}$".format(service))
        except Exception as err:
            print("failed to exec smanager.pl , reason: {}".format(err))
            sys.exit(1)
        if ":" in result:
            host = result.split(":")[1]
            status = result.split(":")[-1]
        else:
            raise Exception("smanager error:{}".format(result))
        return host, status

    def handle(self, **kwargs):
        restda_host, restda_status = self._get_service_node_and_status_by_smanager("restda")
        restda_common_host, restda_common_status = self._get_service_node_and_status_by_smanager("restda-common")
        restda_fm_host, restda_fm_status = self._get_service_node_and_status_by_smanager("restda-fm")
        restda_pm_host, restda_pm_status = self._get_service_node_and_status_by_smanager("restda-pm")
        kwargs.update(dict(restdaHost=restda_host, restdaCommonHost=restda_common_host, restdaFMHost=restda_fm_host,
                           restdaPMHost=restda_pm_host, restdaStatus=restda_status,
                           restdaCommonStatus=restda_common_status,
                           restdaFMStatus=restda_fm_status, restdaPMStatus=restda_pm_status))
        super(SearchService, self).handle(**kwargs)


class EnableRestda(BashHandle):
    def __init__(self):
        super(EnableRestda, self).__init__()

    def handle(self, **kwargs):
        Sed.set(RESTDA_CUSTOMER_PROPERTIES_PATH, ENABLE_FM_ITEM, "true")
        Sed.set(RESTDA_CUSTOMER_PROPERTIES_PATH, ENABLE_PM_ITEM, "true")
        Sed.remote_set(kwargs["restdaHost"], RESTDA_FRONTEND_INTERNAL_PROPERTIES_PATH, ENABLE_STARTUP_ITEM, "true")
        Sed.remote_set(kwargs["restdaCommonHost"], RESTDA_COMMON_INTERNAL_PROPERTIES_PATH, ENABLE_STARTUP_ITEM,
                       "true")
        Sed.remote_set(kwargs["restdaFMHost"], RESTDA_FM_INTERNAL_PROPERTIES_PATH, ENABLE_STARTUP_ITEM, "true")
        Sed.remote_set(kwargs["restdaPMHost"], RESTDA_PM_INTERNAL_PROPERTIES_PATH, ENABLE_STARTUP_ITEM, "true")
        print("Enable Restda Successful.")
        super(EnableRestda, self).handle(**kwargs)


class DisableRestda(BashHandle):
    def __init__(self):
        super(DisableRestda, self).__init__()

    def handle(self, **kwargs):
        Sed.set(RESTDA_CUSTOMER_PROPERTIES_PATH, ENABLE_FM_ITEM, "false")
        Sed.set(RESTDA_CUSTOMER_PROPERTIES_PATH, ENABLE_PM_ITEM, "false")
        print("Disable Restda Successful.")
        super(DisableRestda, self).handle(**kwargs)


class Status(BashHandle):
    def __init__(self):
        super(Status, self).__init__()

    def handle(self, **kwargs):
        restda_fm_enable = Sed.get(RESTDA_CUSTOMER_PROPERTIES_PATH, ENABLE_FM_ITEM)
        restda_pm_enable = Sed.get(RESTDA_CUSTOMER_PROPERTIES_PATH, ENABLE_PM_ITEM)
        frontend_allow_startup = Sed.remote_get(kwargs["restdaHost"],
                                                RESTDA_FRONTEND_INTERNAL_PROPERTIES_PATH,
                                                ENABLE_STARTUP_ITEM)
        common_allow_startup = Sed.remote_get(kwargs["restdaCommonHost"],
                                              RESTDA_COMMON_INTERNAL_PROPERTIES_PATH, ENABLE_STARTUP_ITEM)
        fm_allow_startup = Sed.remote_get(kwargs["restdaFMHost"], RESTDA_FM_INTERNAL_PROPERTIES_PATH,
                                          ENABLE_STARTUP_ITEM)
        pm_allow_startup = Sed.remote_get(kwargs["restdaPMHost"], RESTDA_PM_INTERNAL_PROPERTIES_PATH,
                                          ENABLE_STARTUP_ITEM)
        result = []
        if restda_fm_enable == "true":
            result.append("{:<30}{:>30}".format("Restda-FM Feature", "enable"))
        else:
            result.append("{:<30}{:>30}".format("Restda-FM Feature", "disable"))
        if restda_pm_enable == "true":
            result.append("{:<30}{:>30}".format("Restda-PM Feature", "enable"))
        else:
            result.append("{:<30}{:>30}".format("Restda-PM Feature", "disable"))
        result.append("{:<30}{:>30}".format("Restda Frontend Service", kwargs["restdaStatus"]))
        result.append("{:<30}{:>30}".format("Restda Common Service", kwargs["restdaCommonStatus"]))
        result.append("{:<30}{:>30}".format("Restda FM Service", kwargs["restdaFMStatus"]))
        result.append("{:<30}{:>30}".format("Restda PM Service", kwargs["restdaPMStatus"]))
        if frontend_allow_startup == common_allow_startup == fm_allow_startup == pm_allow_startup == "true":
            result.append("{:<30}{:>30}".format("Small Lab Startup", "allow"))
        else:
            result.append("{:<30}{:>30}".format("Small Lab Startup", "forbid"))
        print("\n".join(result))


class TriggerFullSync(BashHandle):
    def __init__(self):
        super(TriggerFullSync, self).__init__()
        self.db_path = "/var/opt/oss/Nokia-restda-fm/data/restda_system.db"

    def handle(self, **kwargs):
        if not os.path.exists(self.db_path):
            Logger.error("{} is not exist".format(self.db_path))
            Logger.error("Trigger fullsync failed.")
            exit(1)
        update_sql = """echo "update system_parameter set param_value='{value}' where param_key='{key}' ;" |sqlite3 {db}"""
        execute_command(update_sql.format(key="TOPOLOGY_FULL_SYNC_NEEDED", value="yes", db=self.db_path))
        execute_command(update_sql.format(key="TOPOLOGY_LAST_FULL_SYNC_TIME", value="1577687640000",
                                          db=self.db_path))
        execute_command(update_sql.format(key="FM_FULL_SYNC_NEEDED", value="yes", db=self.db_path))
        execute_command(update_sql.format(key="FM_LAST_FULL_SYNC_TIME", value="1577687640000", db=self.db_path))
        Logger.info("Trigger fullsync Successful.")
        super(TriggerFullSync, self).handle(**kwargs)


class CheckFullSync(BashHandle):
    def __init__(self):
        super(CheckFullSync, self).__init__()
        self.db_path = "/var/opt/oss/Nokia-restda-fm/data/restda_system.db"

    def handle(self, **kwargs):
        fm_node = kwargs["restdaFMHost"]
        stdout, stderr, rc = remote_execute_command(fm_node,
                                                    """'echo "select * from system_parameter;" | sqlite3 {db}'""".format(
                                                        db=self.db_path))
        print(stdout)
        super(CheckFullSync, self).handle(**kwargs)


class GetBriefOfService(BashHandle):
    def __init__(self):
        super(GetBriefOfService, self).__init__()

    def handle(self, **kwargs):
        header = ['-H', '"Authorization:Bearer {}"'.format(kwargs["token"]), '-H',
                  '"Content-Type:application/json"', ]
        content = Curl.get("https://{}:9527/restda/api".format(kwargs["fqdn"]), *header)
        if not self.successor:
            print(json.dumps(content, indent=4))
        super(GetBriefOfService, self).handle(**kwargs)


class GetDetailOfService(BashHandle):
    def __init__(self):
        super(GetDetailOfService, self).__init__()

    def handle(self, **kwargs):
        header = ['-H', '"Authorization:Bearer {}"'.format(kwargs["token"]), '-H',
                  '"Content-Type:application/json"', ]
        content = Curl.get("https://{}:9527/restda/api/v1".format(kwargs["fqdn"]), *header)
        if not self.successor:
            print(json.dumps(content, indent=4))
        super(GetDetailOfService, self).handle(**kwargs)


class IssueToken(BashHandle):
    def __init__(self):
        super(IssueToken, self).__init__()

    def handle(self, **kwargs):
        if not kwargs["token"]:
            header = ['-H', '"Content-Type:application/x-www-form-urlencoded"',
                      '-d', '"grant_type=client_credentials"', '-u', '"omc:{}"'.format(kwargs["password"])]
            content = Curl.post("https://{}:9527/restda/oauth2/token".format(kwargs["fqdn"]), *header)
            token = content["token_key"]
            kwargs.update(dict(token=token))
            if not self.successor:
                print(json.dumps(content, indent=4))
        super(IssueToken, self).handle(**kwargs)


class CreatePlans(BashHandle):
    def __init__(self):
        super(CreatePlans, self).__init__()

    @staticmethod
    def _creating(fqdn, token, plan_agreement):
        header = ['-H', '"Authorization:Bearer {}"'.format(token), '-H',
                  '"Content-Type:application/json"', '--data', "'{}'".format(plan_agreement)]
        content = Curl.post("https://{}:9527/restda/api/v1/plans".format(fqdn), *header)
        return content

    def handle(self, **kwargs):
        plan_agreement = file_load(kwargs["file"]) if kwargs["file"] else CreatePlanAgreement.predefined_template(
            kwargs["templateId"], kwargs["type"])
        plan_agreement = json.dumps(plan_agreement)
        if "count" in kwargs and kwargs["count"]:
            for i in range(kwargs["count"]):
                content = self._creating(kwargs["fqdn"], kwargs["token"], plan_agreement)
                plan_id = content["plan_id"]
                status = content["status"]
                print("\t----{}. created {} [PlanId: {}]".format(i + 1, status, plan_id))
        else:
            content = self._creating(kwargs["fqdn"], kwargs["token"], plan_agreement)
            if not self.successor:
                print(json.dumps(content, indent=4))
        super(CreatePlans, self).handle(**kwargs)


class GetPlanList(BashHandle):
    def __init__(self):
        super(GetPlanList, self).__init__()

    def handle(self, **kwargs):
        header = ['-H', '"Authorization:Bearer {}"'.format(kwargs["token"])]
        content = Curl.get("https://{}:9527/restda/api/v1/plans/".format(kwargs["fqdn"]), *header)
        plan_informations = content["plan_informations"]
        plans_id = []
        for plan in plan_informations:
            plan_id = plan["id"]
            plans_id.append(plan_id)
        kwargs.update(dict(plans_id=plans_id))
        if not self.successor:
            print(json.dumps(content, indent=4))
        super(GetPlanList, self).handle(**kwargs)


class GetPlanDetail(BashHandle):
    def __init__(self):
        super(GetPlanDetail, self).__init__()

    def handle(self, **kwargs):
        hearder = ['-H', '"Authorization:Bearer {}"'.format(kwargs["token"])]
        content = Curl.get("https://{}:9527/restda/api/v1/plans/{}".format(kwargs["fqdn"], kwargs["planId"]), *hearder)
        if not self.successor:
            print(json.dumps(content, indent=4))
        super(GetPlanDetail, self).handle(**kwargs)


class GetTemplateList(BashHandle):
    def __init__(self):
        super(GetTemplateList, self).__init__()

    def handle(self, **kwargs):
        header = ['-H', '"Authorization:Bearer {}"'.format(kwargs["token"])]
        content = Curl.get("https://{}:9527/restda/api/v1/templates".format(kwargs["fqdn"]), *header)
        print(json.dumps(content, indent=4))
        super(GetTemplateList, self).handle(**kwargs)


class GetTemplateDetail(BashHandle):
    def __init__(self):
        super(GetTemplateDetail, self).__init__()

    def handle(self, **kwargs):
        header = ['-H', '"Authorization:Bearer {}"'.format(kwargs["token"])]
        content = Curl.get("https://{}:9527/restda/api/v1/templates/{}".format(kwargs["fqdn"], kwargs["templateId"]),
                           *header)
        if not self.successor:
            print(json.dumps(content, indent=4))
        super(GetTemplateDetail, self).handle(**kwargs)


class GetTaskList(BashHandle):
    def __init__(self):
        super(GetTaskList, self).__init__()

    def handle(self, **kwargs):
        header = ['-H', '"Authorization:Bearer {}"'.format(kwargs["token"])]
        if "plan_id" in kwargs and kwargs["plan_id"]:
            url = "https://{}:9527/restda/api/v1/tasks?plan_id={}".format(kwargs["fqdn"], kwargs["plan_id"])
        else:
            url = "https://{}:9527/restda/api/v1/tasks".format(kwargs["fqdn"])
        content = Curl.get(url, *header)
        task_informations = content["taskInformations"]
        successful_task_id = []
        all_task_id = []
        for task in task_informations:
            plan_id = task["id"]
            status = task["status"]
            all_task_id.append(plan_id)
            if status == "successful":
                successful_task_id.append(plan_id)
        kwargs.update(dict(successful_task_id=successful_task_id))
        kwargs.update(dict(all_task_id=all_task_id))
        if not self.successor:
            print(json.dumps(content, indent=4))
        super(GetTaskList, self).handle(**kwargs)


class GetTaskDetail(BashHandle):
    def __init__(self):
        super(GetTaskDetail, self).__init__()

    def handle(self, **kwargs):
        header = ['-H', '"Authorization:Bearer {}"'.format(kwargs["token"])]
        content = Curl.get("https://{}:9527/restda/api/v1/tasks/{}".format(kwargs["fqdn"], kwargs["taskId"]), *header)
        if not self.successor:
            print(json.dumps(content, indent=4))
        super(GetTaskDetail, self).handle()


class GetTasksDetail(BashHandle):
    def __init__(self):
        super(GetTasksDetail, self).__init__()

    def handle(self, **kwargs):
        successful_task_length = len(kwargs["successful_task_id"])
        print("searched {} successful tasks".format(successful_task_length))
        print("searching result file url...")
        result_files_href = []
        for i, taskId in enumerate(kwargs["successful_task_id"]):
            header = ['-H', '"Authorization:Bearer {}"'.format(kwargs["token"])]
            content = Curl.get("https://{}:9527/restda/api/v1/tasks/{}".format(kwargs["fqdn"], taskId), *header)
            status = content["status"]
            if status == "successful":
                result_href = content["resultHref"]
                result_files_href.append(result_href)
            sys.stdout.write('\rsearched {}/{}'.format(i + 1, successful_task_length))
            sys.stdout.flush()
        print("")
        kwargs.update(dict(result_files_href=result_files_href))
        super(GetTasksDetail, self).handle(**kwargs)


class Downloads(BashHandle):
    def __init__(self):
        super(Downloads, self).__init__()

    @staticmethod
    def _downloading(url, token):
        header = ['-H', '"Accept:application/octet-stream"', '-H', '"Authorization:Bearer {}"'.format(token)]
        content = Curl.download(url, *header)
        return content

    def handle(self, **kwargs):
        if "taskId" in kwargs and kwargs["taskId"]:
            url = "https://{}:9527/restda/api/v1/results/{}".format(kwargs["fqdn"], kwargs["taskId"])
            content = self._downloading(url, kwargs["token"])
            print(content)
        else:
            for i, href in enumerate(kwargs["result_files_href"]):
                url = "https://{}:9527/restda/api{}".format(kwargs["fqdn"], href)
                content = self._downloading(url, kwargs["token"])
                print("{}.".format(i + 1), content)
        super(Downloads, self).handle(**kwargs)


class DeletePlans(BashHandle):
    def __init__(self):
        super(DeletePlans, self).__init__()

    @staticmethod
    def _deleting(fqdn, token, plan_id):
        header = ['-H', '"Authorization:Bearer {}"'.format(token)]
        content = Curl.delete(
            "https://{}:9527/restda/api/v1/plans?planId={}".format(fqdn, plan_id), *header)
        return content

    def handle(self, **kwargs):
        if "planId" in kwargs and kwargs["planId"]:
            content = self._deleting(kwargs["fqdn"], kwargs["token"], kwargs["planId"])
            if not self.successor:
                print(json.dumps(content, indent=4))
        elif "plans_id" in kwargs and kwargs["plans_id"]:
            for i, planId in enumerate(kwargs["plans_id"]):
                content = self._deleting(kwargs["fqdn"], kwargs["token"], planId)
                status = content["status"]
                print("\t----{}. deleted {} [PlanId: {}]".format(i + 1, status, planId))
        super(DeletePlans, self).handle(**kwargs)


class DeleteTasks(BashHandle):
    def __init__(self):
        super(DeleteTasks, self).__init__()

    @staticmethod
    def _deleting_by_task_id(fqdn, token, task_id):
        header = ['-H', '"Authorization:Bearer {}"'.format(token)]
        content = Curl.delete("https://{}:9527/restda/api/v1/tasks?taskId={}".format(fqdn, task_id), *header)
        return content

    @staticmethod
    def _deleting_by_plan_id(fqdn, token, plan_id):
        header = ['-H', '"Authorization:Bearer {}"'.format(token)]
        content = Curl.delete("https://{}:9527/restda/api/v1/tasks?planId={}".format(fqdn, plan_id), *header)
        return content

    def handle(self, **kwargs):
        if "taskId" in kwargs and kwargs["taskId"]:
            content = self._deleting_by_task_id(kwargs["fqdn"], kwargs["token"], kwargs["taskId"])
            if not self.successor:
                print(json.dumps(content, indent=4))
        elif "planId" in kwargs and kwargs["planId"]:
            content = self._deleting_by_plan_id(kwargs["fqdn"], kwargs["token"], kwargs["planId"])
            if not self.successor:
                print(json.dumps(content, indent=4))
        else:
            for i, taskId in enumerate(kwargs["all_task_id"]):
                header = ['-H', '"Authorization:Bearer {}"'.format(kwargs["token"])]
                content = Curl.delete("https://{}:9527/restda/api/v1/tasks?taskId={}".format(kwargs["fqdn"], taskId),
                                      *header)
                if 'result' in content:
                    status = content["result"]
                else:
                    status = content['errorCode']
                print("\t----{}. deleted {} [TaskId: {}]".format(i + 1, status, taskId))
        super(DeleteTasks, self).handle(**kwargs)


class ParameterParser(object):
    _templateList = ["Predefined_topologyAdvanced_v1",
                     "Predefined_activeAlarms_v1",
                     "Predefined_activeAlarms_v2",
                     "Predefined_activeAlarms_v3",
                     "Predefined_historyFMAlarms_v1",
                     "Predefined_alarmDelta_v1",
                     "Predefined_topologyOfActiveAlarms_v1",
                     "Predefined_topologyOfActiveAlarms_v2",
                     "Predefined_performanceData_v1"]
    _mandatoryParameterList = ["getBriefOfService", "getDetailOfService",
                               "issueToken",
                               "getTemplateList", "getTemplateDetail",
                               "newPlans", "getPlanList", "getPlanDetail", "deletePlan", "deleteAllPlans",
                               "getTaskList", "getTaskDetail", "deleteTasks", "deleteAllTasks",
                               "downloadResult",
                               "enable", "disable", "status",
                               "triggerFullSync", "checkFullSync"
                               ]

    def __init__(self):
        super(ParameterParser, self).__init__()
        self._init_parameter()

    @property
    def mandatory_parameter_list(self):
        return self._mandatoryParameterList

    @property
    def type_list(self):
        return CreatePlanAgreement.typeList

    @property
    def template_list(self):
        return self._templateList

    @property
    def _mandatory_group(self):
        group = optparse.OptionGroup(self.opt, "Mandatory Options:")
        group.add_option("-o", action='store', dest='operation', choices=self.mandatory_parameter_list,
                         help="should be choice from {}".format(self.mandatory_parameter_list))
        return group

    @property
    def _optional_group(self):
        group = optparse.OptionGroup(self.opt, "Optional Options:")
        group.add_option("--lbwas", action='store', dest='lbwas', metavar='clabxxxlbwas.netact.nsn-rdnet.net',
                         help='specific url')
        group.add_option("--user", action='store', dest='user', metavar='omc', default='omc', help='specific user')
        group.add_option("--password", action='store', dest='password', metavar='omc', help='specific password')
        group.add_option("--token", action='store', dest='token', help='specific token')
        group.add_option("--debug", action='store_true', dest='debug', help='print debug message.')
        group.add_option("--ignoreError", action='store_true', dest='ignore')
        return group

    @property
    def _additional_group(self):
        group = optparse.OptionGroup(self.opt, "Additional Options:")
        group.add_option("--type", action='store', dest='type', type="choice",
                         choices=self.type_list, default="oneTime", metavar="oneTime",
                         help="for newPlans, should be choice from {}".format(self.type_list))
        group.add_option("--file", action='store', dest='file', metavar='file path',
                         help='specific json file for newPlans')
        group.add_option("--count", action='store', dest='count', metavar='int', help='specific count for newPlans',
                         type="int")
        group.add_option("--planId", action='store', dest='planId', metavar='int', type="int")
        group.add_option("--templateId", action='store', dest='templateId', choices=self.template_list,
                         help="should be choice from {}".format(self.template_list))
        group.add_option("--taskId", action='store', dest='taskId', metavar='int', type="int")
        return group

    def _init_parameter(self):
        self.opt = optparse.OptionParser(version='2.0', usage="use --help,-h to see cookbook")
        self.opt.add_option_group(self._mandatory_group)
        self.opt.add_option_group(self._optional_group)
        self.opt.add_option_group(self._additional_group)
        self.options, self.args = self.opt.parse_args()

    def parse(self):
        self._is_valid_for_parameters()
        global DEBUG, IGNORE
        DEBUG = self.options.debug
        IGNORE = self.options.ignore
        return self.options, self.args

    def _is_valid_for_parameters(self):
        try:
            self._is_valid_for_mandatory_parameters()
            self._is_valid_for_additional_parameters()
        except Exception as err:
            self.opt.error("{}".format(err))

    def _is_valid_for_mandatory_parameters(self):
        assert self.options.operation, "-o is missing"

    def _is_valid_for_additional_parameters(self):
        if self.options.file:
            assert os.path.exists(self.options.file), "file {} is missing".format(self.options.file)
            assert os.path.isfile(self.options.file), "file {} is not file".format(self.options.file)
        if self.options.operation == "newPlans":
            assert self.options.type in self.type_list, "--type should be choice from {}".format(
                self.type_list)
            assert self.options.templateId in self.template_list, "--templateId should be choice from {}".format(
                self.template_list)
        if self.options.operation in ["getPlanDetail", "deletePlan"]:
            assert self.options.planId, "--planId is missing"
        if self.options.operation == "getTemplateDetail":
            assert self.options.templateId, "--templateId is missing , choice from {}".format(self.template_list)
        if self.options.operation == "getTaskDetail":
            assert self.options.taskId, "--taskId is missing"
        if self.options.operation == "deleteTasks":
            assert any([self.options.planId, self.options.taskId]), "--planId or --taskId is missing"


def file_load(path):
    with open(path) as f:
        content = f.read()
    plan_json = json.loads(content)
    return plan_json


class ChainBuilder(object):
    _chainMap = dict(
        getBriefOfService=[GetLBWAS, GetPassword, IssueToken, GetBriefOfService],
        getDetailOfService=[GetLBWAS, GetPassword, IssueToken, GetDetailOfService],
        issueToken=[GetLBWAS, GetPassword, IssueToken],
        newPlans=[GetLBWAS, GetPassword, IssueToken, CreatePlans],
        getPlanList=[GetLBWAS, GetPassword, IssueToken, GetPlanList],
        getPlanDetail=[GetLBWAS, GetPassword, IssueToken, GetPlanDetail],
        deletePlan=[GetLBWAS, GetPassword, IssueToken, DeletePlans],
        deleteAllPlans=[GetLBWAS, GetPassword, IssueToken, GetPlanList, DeletePlans],
        getTemplateList=[GetLBWAS, GetPassword, IssueToken, GetTemplateList],
        getTemplateDetail=[GetLBWAS, GetPassword, IssueToken, GetTemplateDetail],
        getTaskList=[GetLBWAS, GetPassword, IssueToken, GetTaskList],
        getTaskDetail=[GetLBWAS, GetPassword, IssueToken, GetTaskDetail],
        downloadResult=[GetLBWAS, GetPassword, IssueToken, GetTaskList, GetTasksDetail, Downloads],
        deleteTasks=[GetLBWAS, GetPassword, IssueToken, DeleteTasks],
        deleteAllTasks=[GetLBWAS, GetPassword, IssueToken, GetTaskList, DeleteTasks],
        enable=[SearchService, EnableRestda],
        disable=[SearchService, DisableRestda],
        status=[SearchService, Status],
        triggerFullSync=[TriggerFullSync],
        checkFullSync=[SearchService, CheckFullSync],
    )

    @staticmethod
    def _init_chain(*args):
        step_list = []
        for step in args:
            if isinstance(step, type):
                step = step()
            step_list.append(step)
        length = len(args)
        for i in range(length):
            if i + 2 <= length:
                step = step_list[i]
                next_step = step_list[i + 1]
                step.successor = next_step
        return step_list[0]

    @classmethod
    def build(cls, name):
        assert name in cls._chainMap, "ChainBuilder invalid build {}".format(name)
        chain = cls._chainMap[name]
        first_of_chain = cls._init_chain(*chain)
        return first_of_chain


def main():
    parser = ParameterParser()
    options, args = parser.parse()
    kick_off = ChainBuilder.build(options.operation)
    kick_off.handle(file=options.file, token=options.token, password=options.password, type=options.type,
                    taskId=options.taskId, templateId=options.templateId,
                    planId=options.planId, count=options.count, user=options.user,
                    lbwas=options.lbwas)


if __name__ == "__main__":
    main()
