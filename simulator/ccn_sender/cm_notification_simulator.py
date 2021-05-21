import subprocess
import logging
import re
import time
import os
import optparse
import signal
import sys
from os.path import dirname, abspath, join, exists, isfile, isabs
import datetime
import random
import traceback


def singleton(cls, *args, **kwargs):
    instances = dict()

    def _singleton():
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return _singleton


class Logger(object):
    logger = logging.getLogger("Logger")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s: %(message)s')
    handler = logging.FileHandler(join(dirname(abspath(__file__)), 'cm_notification_simulator.log'), 'w')
    # handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    @classmethod
    def info(cls, message):
        cls.logger.info(cls._strip(message))

    @classmethod
    def error(cls, message):
        cls.logger.error(cls._strip(message))
        print(message)

    @classmethod
    def debug(cls, message):
        cls.logger.debug(cls._strip(message))

    @classmethod
    def warning(cls, message):
        cls.logger.warning(cls._strip(message))

    @classmethod
    def enable_debug(cls):
        cls.logger.setLevel(logging.DEBUG)
        cls.debug("enable debug level.")

    @staticmethod
    def _strip(message):
        if isinstance(message, bytes):
            message = message.strip()
        elif isinstance(message, str):
            message = message.strip()
        return message


def execute_command(command):
    command = command.strip()
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    stdout = stdout.strip()
    stderr = stderr.strip()
    rc = process.returncode
    Logger.debug("execute: {}".format(command))
    Logger.debug("stdout: {}".format(stdout))
    Logger.debug("stderr: {}".format(stderr))
    Logger.debug("rc: {}".format(rc))
    return stdout.decode("utf-8"), stderr.decode("utf-8"), rc


def execute_sqlplus_command(sql, user='omc', password='omc'):
    command = 'echo -e "set head off;\n set linesize 2000;\n {sql};" | sqlplus -s {user}/{password}'.format(
        sql=sql.rstrip(';'),
        user=user,
        password=password)
    Logger.debug(sql)
    stdout, stderr, rc = execute_command(command)
    if rc == 0:
        return stdout
    else:
        Logger.error(stderr)
        exit(1)


content_head = """<operation type="{type}" xmlns="http://operation.test.nbi.oss.nsn.com">\n<networkElements>"""
content_tail = """\n</networkElements>\n</operation>"""
attr_template = "<property><name>{attr}</name><value>{value}</value></property>"
mo_template = """<networkElement dn="{dn}"><rac clazz="{clazz}" version="{version}">{attrs}</rac></networkElement>"""
"""<nasda clazz="{clazz}" version="1.0"></nasda>"""


class CMNotification(object):
    def __init__(self, constant, burst):
        super(CMNotification, self).__init__()
        self._lbwas = None
        self.ractoolsmx = "/opt/oss/NSN-cmplatform/bin/ractoolsmx.sh"
        self.manageObjects = "/home/omc/manageObjectSim.jar"
        self.iterator = 0
        self._existMoList = []
        self._model = []
        self.constant = constant
        self.burst = burst

    @staticmethod
    def _get_today_timestamp(_date="00:00"):
        return datetime.datetime.strptime(str(datetime.datetime.now().date()) + _date, '%Y-%m-%d%H:%M')

    def _get_burst_time_range(self):
        return [(self._get_today_timestamp("00:00"), self._get_today_timestamp("00:05")),
                (self._get_today_timestamp("02:00"), self._get_today_timestamp("02:05")),
                (self._get_today_timestamp("04:00"), self._get_today_timestamp("04:05")),
                (self._get_today_timestamp("06:00"), self._get_today_timestamp("06:05")),
                (self._get_today_timestamp("08:00"), self._get_today_timestamp("08:05")),
                (self._get_today_timestamp("10:00"), self._get_today_timestamp("10:05")),
                (self._get_today_timestamp("12:00"), self._get_today_timestamp("12:05")),
                (self._get_today_timestamp("14:00"), self._get_today_timestamp("14:05")),
                (self._get_today_timestamp("16:00"), self._get_today_timestamp("16:05")),
                (self._get_today_timestamp("18:00"), self._get_today_timestamp("18:05")),
                (self._get_today_timestamp("20:00"), self._get_today_timestamp("20:05")),
                (self._get_today_timestamp("22:00"), self._get_today_timestamp("22:05"))]

    def _is_burst(self):
        current_time = datetime.datetime.now()
        burst_time_range_list = self._get_burst_time_range()
        for burst_time_range in burst_time_range_list:
            _burst_start = burst_time_range[0]
            _burst_end = burst_time_range[1]
            if _burst_start < current_time < _burst_end:
                return True
        return False

    @property
    def target_throughput(self):
        if self._is_burst():
            return self.burst
        else:
            return self.constant

    @staticmethod
    def _get_lbwas():
        stdout, stderr, rc = execute_command("/opt/cpf/bin/cpf_list_lb_address.sh --lb was")
        if rc == 0:
            return stdout
        else:
            Logger.error("get lb was failed: {}".format(stderr))
            exit(1)

    @property
    def lbwas(self):
        if not self._lbwas:
            self._lbwas = self._get_lbwas()
        return self._lbwas

    def send_notification(self, home_path, model_file, instance, window, max_runtime):
        if window < 10:
            raise Exception("window is too small")
        model = self.model(model_file)
        mo_count = len(model)
        total_notification_count = 0
        styles = ">" * 45
        Logger.info("{style}Loading{style}".format(style=styles))
        self.get_mrbts(instance)
        Logger.info("{style}Loaded{style}".format(style=styles))
        standbytime = time.time()
        records = []
        while 1:
            if max_runtime and time.time() - standbytime > max_runtime:
                Logger.info("max runtime: {}s reached.".format(max_runtime))
                break
            Logger.info("{style}Sending{style}".format(style=styles))
            # start_time = time.time()
            notification_count = 0
            self.iterator += 1
            if not self.is_mo_exist(instance, self.iterator):  # add notification
                importing_time = time.time()
                status = self.send_create_notification(home_path, model_file, instance, self.iterator)
                if status:
                    notification_count += mo_count
                    records.append((importing_time, mo_count))
                    self.sleepping(records, self.target_throughput)
            if self.iterator > window:  # modify notification
                for i in range(8):
                    importing_time = time.time()
                    # status = self.send_update_notification(home_path, model_file, instance, window, not bool(i % 2))
                    status = self.send_update_notification(home_path, model_file, instance, self.iterator - window + i)
                    if status:
                        notification_count += mo_count
                        records.append((importing_time, mo_count))
                        self.sleepping(records, self.target_throughput)
                    else:
                        break
            if self.iterator > window * 2:  # delete notification
                importing_time = time.time()
                status = self.send_delete_notification(home_path, model_file, instance, self.iterator - 2 * window)
                if status:
                    notification_count += mo_count
                    records.append((importing_time, mo_count))
                    self.sleepping(records, self.target_throughput)
            total_notification_count += notification_count
            _, _, last_5min_avg_throughput, _, _, last_15min_avg_throughput, _, _, last_60min_avg_throughput = self.average_throughput(
                records)
            Logger.info("| {:^30} | {:^30} | {:^30} |".format("last 5min avg-throughout", "last 15min avg-throughout",
                                                              "last 60min avg-throughout", "total notification count"))
            Logger.info(
                "| {:^30} | {:^30} | {:^30} |".format(int(last_5min_avg_throughput), int(last_15min_avg_throughput),
                                                      int(last_60min_avg_throughput), total_notification_count))
        Logger.info("exit send_notification")

    def send_create_notification(self, home_path, model_file, instance, identifier):
        _start_time = time.time()
        target_file_name = ".{}_{}_add.xml".format(instance, identifier)
        target_file = join(home_path, target_file_name)
        # parameter is not specified
        self.generate_configuration(model_file, target_file, instance, identifier, bare=False, type_name="add",
                                    attr_change=False)
        status = self.manage_objects(target_file)
        _cost_time = time.time() - _start_time
        if status:
            Logger.info("| {:^30} | {:^30} | {:^30} |".format("send create notification",
                                                              "object: MRBTS-{}_{}".format(instance, self.iterator),
                                                              "{}s".format(_cost_time)))
        else:
            Logger.info("| {:^30} | {:^30} | {:^30} |".format("send create notification failed",
                                                              "object: MRBTS-{}_{}".format(instance, self.iterator),
                                                              "{}s".format(_cost_time)))
        return status

    def send_update_notification(self, home_path, model_file, instance, identifier, bare=False, attr_change=True):
        _start_time = time.time()
        target_file_name = ".{}_{}_modify.xml".format(instance, identifier)
        target_file = join(home_path, target_file_name)
        self.generate_configuration(model_file, target_file, instance, identifier, bare=bare, type_name="modify",
                                    attr_change=attr_change)
        status = self.manage_objects(target_file)
        _cost_time = time.time() - _start_time
        if status:
            Logger.info("| {:^30} | {:^30} | {:^30} |".format("send change notification",
                                                              "object: MRBTS-{}_{}".format(instance, identifier),
                                                              "{}s".format(_cost_time)))
        else:
            Logger.info("| {:^30} | {:^30} | {:^30} |".format("send change notification failed",
                                                              "object: MRBTS-{}_{}".format(instance, identifier),
                                                              "{}s".format(_cost_time)))
        return status

    def send_delete_notification(self, home_path, model_file, instance, identifier):
        _start_time = time.time()
        target_file_name = ".{}_{}_delete.xml".format(instance, identifier)
        target_file = join(home_path, target_file_name)
        # parameter is not specified
        self.generate_configuration(model_file, target_file, instance, identifier, bare=True, type_name="delete",
                                    attr_change=False)
        status = self.manage_objects(target_file)
        _cost_time = time.time() - _start_time
        if status:
            Logger.info("| {:^30} | {:^30} | {:^30} |".format("send delete notification",
                                                              "object: MRBTS-{}_{}".format(instance, identifier),
                                                              "{}s".format(_cost_time)))
        else:
            Logger.info("| {:^30} | {:^30} | {:^30} |".format("send delete notification failed",
                                                              "object: MRBTS-{}_{}".format(instance, identifier),
                                                              "{}s".format(_cost_time)))
        return status

    def sleepping(self, records, target_throughput):
        last_5min_throughput, last_5min_cost, last_5min_avg_throughput, last_15min_throughput, last_15min_cost, last_15min_avg_throughput, last_60min_throughput, last_60min_cost, last_60min_avg_throughput = self.average_throughput(
            records)
        if last_5min_throughput:
            if last_5min_avg_throughput > target_throughput:
                sleep_time = last_5min_throughput / target_throughput - last_5min_cost
                if sleep_time > 0:
                    Logger.info("| {:^30} | {:^30} |".format("sleepping", "{}s".format(sleep_time)))
                    time.sleep(sleep_time)
        elif last_15min_throughput:
            if last_15min_avg_throughput > target_throughput:
                sleep_time = last_15min_throughput / target_throughput - last_15min_cost
                if sleep_time > 0:
                    Logger.info("| {:^30} | {:^30} |".format("sleepping", "{}s".format(sleep_time)))
                    time.sleep(sleep_time)
        elif last_60min_throughput:
            if last_60min_avg_throughput > target_throughput:
                sleep_time = last_60min_throughput / target_throughput - last_60min_cost
                if sleep_time > 0:
                    Logger.info("| {:^30} | {:^30} |".format("sleepping", "{}s".format(sleep_time)))
                    time.sleep(sleep_time)

    @staticmethod
    def average_throughput(records):
        current_time = time.time()
        last_5min_time = current_time - 5 * 60
        last_15min_time = current_time - 15 * 60
        last_60min_time = current_time - 60 * 60
        last_5min_records = list(filter(lambda record: record[0] > last_5min_time, records))
        last_15min_records = list(filter(lambda record: record[0] > last_15min_time, records))
        last_60min_records = list(filter(lambda record: record[0] > last_60min_time, records))
        if records:
            if last_5min_records:
                last_5min_cost = current_time - last_5min_records[0][0]
                last_5min_throughput = sum(list(map(lambda record: record[1], last_5min_records)))
                last_5min_avg_throughput = last_5min_throughput / last_5min_cost
            else:
                last_5min_cost, last_5min_throughput, last_5min_avg_throughput = 0, 0, 0
            if last_15min_records:
                last_15min_cost = current_time - last_15min_records[0][0]
                last_15min_throughput = sum(list(map(lambda record: record[1], last_15min_records)))
                last_15min_avg_throughput = last_15min_throughput / last_15min_cost
            else:
                last_15min_cost, last_15min_throughput, last_15min_avg_throughput = 0, 0, 0
            if last_60min_records:
                last_60min_cost = current_time - last_60min_records[0][0]
                last_60min_throughput = sum(list(map(lambda record: record[1], last_60min_records)))
                last_60min_avg_throughput = last_60min_throughput / last_60min_cost
            else:
                last_60min_cost, last_60min_throughput, last_60min_avg_throughput = 0, 0, 0
            return last_5min_throughput, last_5min_cost, last_5min_avg_throughput, last_15min_throughput, last_15min_cost, last_15min_avg_throughput, last_60min_throughput, last_60min_cost, last_60min_avg_throughput
        else:
            return 0, 0, 0, 0, 0, 0, 0, 0, 0

    def is_mo_exist(self, instance, iterator):
        exist_mrbts_list = self.get_mrbts(instance)
        Logger.debug("exist mo list: {}".format(exist_mrbts_list))
        mrbts_path = 'PLMN-PLMN/MRBTS-{}_{}'.format(instance, iterator)
        if mrbts_path in exist_mrbts_list:
            Logger.info("| {:^30} | {:^30} | {:^30} |".format("send create notification",
                                                              "object: MRBTS-{}_{}".format(instance, self.iterator),
                                                              "object already exist"))
            return True
        else:
            Logger.debug("{} is not exist".format(mrbts_path))
            return False

    def manage_objects(self, file_path, retry=3):
        status = 1
        for i in range(retry):
            command = "java -jar {} --ip {} --file {}".format(self.manageObjects, self.lbwas, file_path)
            Logger.debug(command)
            stdout, stderr, rc = execute_command(command)
            if rc or stderr or 'error' in stdout.lower():
                Logger.debug("stdout: {}".format(stdout))
                Logger.debug("stderr: {}".format(stderr))
                Logger.warning("execute command failed: {}, try again later".format(command))
                time.sleep(3)
            else:
                if exists(file_path) and isfile(file_path):
                    os.remove(file_path)
                status = 0
                break
        if status:
            # failed
            Logger.error("execute manageObjectSim.jar failed in 3 times")
            return False
        else:
            return True

    def check_tool(self):
        if not (exists(self.ractoolsmx) and isfile(self.ractoolsmx)):
            Logger.error("script is only running on was node!")
            exit(1)
        if not (exists(self.manageObjects) and isfile(self.manageObjects)):
            Logger.error("{} is not ready!".format(self.manageObjects))
            exit(1)

    def generate_configuration(self, model_file, target_file, instance, iterator, bare=False, type_name="add",
                               attr_change=False):
        starttime = time.time()
        network_elements = self.generate_mo_by_model(model_file, instance, iterator, bare, attr_change)
        mo_count = len(network_elements)
        with open(target_file, "wb") as f:
            f.write(content_head.format(type=type_name).encode('utf-8'))
            f.write('\n'.join(network_elements).encode('utf-8'))
            f.write(content_tail.encode('utf-8'))
        Logger.debug(
            "-- Generated cm objects file {}, MRBTS Name : {}_{}, sub-objects count: {}, cost: {}s".format(target_file,
                                                                                                           instance,
                                                                                                           iterator,
                                                                                                           mo_count,
                                                                                                           time.time() - starttime))
        return mo_count

    def get_mrbts(self, instance):
        if not self._existMoList:
            Logger.debug("-- Get exist CM objects list")
            command = """
            select co_dn from ctp_common_objects where co_dn like '%PLMN-PLMN/MRBTS-{name}%' and co_dn not like '%PLMN-PLMN/MRBTS-{name}%/%';
            """.format(name=instance).strip()
            stdout = execute_sqlplus_command(command)
            for line in stdout.split("\n"):
                self._existMoList.append(line.strip())
        return self._existMoList

    def generate_mo_by_model(self, model_file, instance, iterator, bare, attr_change=False):
        model = self.model(model_file)
        network_elements = []
        _random_str = random.randint(10 ** 5, 10 ** 6)
        for index, row in enumerate(model):
            mrbts_id = "{}_{}".format(instance, iterator)
            dn_path = row.split(",")[0].format(MRBTSID=mrbts_id)
            # object_name = "{} name".format(dn_path.split("/")[-1].lower()).replace("-"," ").replace("_"," ")
            attrs = eval(row.split(",")[1].replace(";", ","))
            # attrs.update({"name": object_name})
            version = attrs.pop("$version")
            clazz = attrs.pop("$class")
            # attrs.update({"name": "alias_{}_{}".format(index, _random_str)})
            attrs_string_list = []
            for attr_name in attrs:
                if not attr_name.startswith("$"):
                    if ":" in attr_name:
                        Logger.debug("Mo: {}, attr: {} , ignore".format(dn_path, attr_name, attrs[attr_name]))
                    else:
                        if not bare:
                            attr_value = attrs[attr_name].format(MRBTSID=mrbts_id)
                            if attr_change and attr_name in ("mnc", "mcc", "latitude", "longitude"):
                                # change attr if attr is number like as 1001,500,776565...
                                attr_value = str(int(attr_value) + 1)
                            attrs_string_list.append(attr_template.format(attr=attr_name, value=attr_value))
            mo_string = mo_template.format(dn=dn_path, version=version, clazz=clazz, attrs="".join(attrs_string_list))
            network_elements.append(mo_string)
        return network_elements

    def model(self, model_file):
        if not self._model:
            with open(model_file, "rb") as f:
                lines = f.readlines()
            lines = list(map(lambda line: line.decode('utf-8'), lines))
            self._model = lines
        return self._model


@singleton
class ModelFile(object):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.metadata_home = "/etc/opt/oss/global/rac/conf/metadata"
        self.metadata_lab_map = {}
        self.model_file_map = {}
        self.need_updated_metadata = ["MRBTS", "TNL", "MNL", "EQMR", "FL", "EQM"]

    def get_metadata_version(self, metadata_name, exclude=''):
        command = "ls {metadata_folder}/* |grep {metadata}".format(metadata_folder=self.metadata_home,
                                                                   metadata=metadata_name)
        stdout, stderr, rc = execute_command(command)
        if rc != 0:
            Logger.error("search metadata file failed")
            exit(1)
        metadata_list = stdout.split("\n")
        Logger.debug(metadata_list)
        metadata_filtered_list = list(filter(lambda x: exclude not in x, metadata_list))
        Logger.debug(metadata_filtered_list)
        metadata_filtered_list = list(filter(lambda x: len(x.split("_")) == 3, metadata_filtered_list))
        _pattern = r"^{}\d+.*".format(metadata_name)
        pattern = re.compile(_pattern)
        metadata_filtered_list = list(filter(lambda x: pattern.match(x), metadata_filtered_list))
        Logger.debug(metadata_filtered_list)
        metadata_filtered_list.sort(key=lambda x: "{}{}".format(x.split("_")[-2], x.split("_")[-1]))
        return metadata_filtered_list

    def search_lab_metadata(self, use_oldest_metadata):
        Logger.info("search metadata in lab.")
        for metadata_name in self.need_updated_metadata:
            metadata_list = self.get_metadata_version(metadata_name, exclude='5G')
            if use_oldest_metadata:
                selected_metadata = metadata_list[0]
            else:
                selected_metadata = metadata_list[-1]
            self.metadata_lab_map.update({metadata_name: selected_metadata})
            Logger.info("lab-> {}: {}".format(metadata_name, selected_metadata))

    def search_model_metadata(self, model_file):
        Logger.info("search metadata in model file: {}.".format(model_file))
        metadata_set = set()
        with open(model_file, "rb") as f:
            lines = f.readlines()
            lines = list(map(lambda line: line.decode('utf-8'), lines))
        for line in lines:
            _line = line.split(",")
            # dn = _line[0]
            args = _line[-1].replace(";", ",")
            _args = eval(args)
            metadata = _args["$version"]
            metadata_set.update({metadata})
        for metadata_name in self.need_updated_metadata:
            metadata = self._get_matched_metadata(metadata_set, metadata_name)
            self.model_file_map.update({metadata_name: metadata})
            Logger.info("model file-> {}: {}".format(metadata_name, metadata))

    @staticmethod
    def _get_matched_metadata(metadata_set, metadata_name):
        for metadata in metadata_set:
            if metadata.startswith(metadata_name):
                return metadata
        Logger.warning("metadata set {} has not metadata: {}".format(metadata_set, metadata_name))

    def update_metadata_version(self, model_file, use_oldest_metadata=False):
        modified_model_file = "{}_modified.csv".format(model_file.split(".")[0])
        self.search_model_metadata(model_file)
        self.search_lab_metadata(use_oldest_metadata)
        self._update_metadata_version(model_file, modified_model_file)
        return modified_model_file

    def _update_metadata_version(self, source_model_file, target_model_file):
        Logger.info("update metadata and save to file: {}".format(target_model_file))
        with open(source_model_file, "rb") as f:
            lines = f.readlines()
            lines = list(map(lambda line: line.decode('utf-8'), lines))
        new_lines = []
        for line in lines:
            _line = line.split(",")
            dn = _line[0]
            args = _line[-1].replace(";", ",")
            _args = eval(args)
            model_metadata = _args["$version"]
            for metadata_name in self.need_updated_metadata:
                if model_metadata.startswith(metadata_name):
                    lab_metadata = self._get_matched_metadata(self.metadata_lab_map.values(), metadata_name)
                    _args.update({"$version": lab_metadata})
                    break
            new_args = str(_args)
            new_args = new_args.replace(",", ";")
            new_line = ",".join([dn, new_args])
            new_lines.append(new_line)

        with open(target_model_file, "wb") as f:
            f.write("\n".join(new_lines).encode('utf-8'))


def exit_tool(sig, frame):
    Logger.debug('Press Ctrl+C, exit.')
    exit(0)


def args_parser():
    opt = optparse.OptionParser(version="1.0")
    opt.add_option("--model", action='store',
                   help="modle csv file, default: napet_lte_model_for_n20_core_ran_filtered.csv",
                   dest="model",
                   default='napet_lte_model_for_n20_core_ran_filtered.csv')
    opt.add_option("--instance", action='store', help="instance of MRBTS, default is Notifier", dest="instance",
                   default="Notifier")
    opt.add_option("--constant", action='store', help="throughput of normal scenario, default is 166/s", type=int,
                   dest="constant", default=166)
    opt.add_option("--burst", action='store', help="throughput of burst scenario, default is 333/s", type=int,
                   dest="burst", default=333)
    opt.add_option("--window", action='store', help="window of CM Notification, default is 10", type=int,
                   dest="window", default=10)
    opt.add_option("--maxRuntime", action='store', help="max runtime of CM Notification, default is unlimited",
                   type=int,
                   dest="maxRuntime", default=0)
    opt.add_option("--debug", action='store_true', help="debug level", dest="debug", default=False)
    _options, _args = opt.parse_args()
    return _options


def runtime_env_check(home_path, _options):
    manage_object_simulator = "/home/omc/manageObjectSim.jar"
    if _options.debug:
        Logger.enable_debug()
    if not isabs(_options.model):
        _options.model = os.path.join(home_path, _options.model)
    if not (os.path.exists(_options.model) and os.path.isfile(_options.model)):
        Logger.error("model file: {} is not exist.".format(_options.model))
        exit(1)
    if not (os.path.exists(manage_object_simulator) and os.path.isfile(manage_object_simulator)):
        Logger.error("{} is not exist.".format(manage_object_simulator))
        exit(1)
    if not (os.path.exists(ModelFile().metadata_home) and os.path.isdir(ModelFile().metadata_home)):
        Logger.error("metadata folder {} is not exist.".format(ModelFile().metadata_home))
        exit(1)


class Deamon(object):
    def __init__(self, home_path, model, instance, constant, burst, window, max_runtime):
        super(Deamon, self).__init__()
        self.running = True
        self.home_dir = home_path
        self.model = model
        self.instance = instance
        self.constant = constant
        self.burst = burst
        self.window = window
        self.maxRuntime = max_runtime

    def stop(self):
        self.running = False

    def fork(self):
        try:
            pid = os.fork()
        except OSError as err:
            Logger.error('fork error: {}'.format(err))
            sys.exit(1)
        if pid == 0:
            # this is child process
            os.chdir("/")
            os.setsid()
            os.umask(0)
            # fork a Grandson process, and child process exit
            try:
                pid = os.fork()
                if pid > 0:
                    # exit child process
                    sys.exit(0)
            except OSError as err:
                Logger.error('fork error: {}'.format(err))
                sys.exit(1)
            # this is Grandson process
            self.run()
            # exit Grandson process
            Logger.info("exit Daemon process")
            sys.exit(0)
        else:
            # this is parent process . nothing to do.
            pass

    def run(self):
        try:
            CMNotification(self.constant, self.burst).send_notification(self.home_dir, self.model, self.instance,
                                                                        self.window, self.maxRuntime)
        except Exception as err:
            Logger.error("daemon Exception: {}".format(err))
            Logger.error("traceback: {}".format(traceback.format_exc()))
        finally:
            Logger.info("exit daemon")


if __name__ == '__main__':
    signal.signal(signal.SIGINT, exit_tool)
    options = args_parser()
    home_dir = dirname(abspath(__file__))
    style = "*" * 20
    Logger.info("{style}Parameters{style}".format(style=style))
    Logger.info("model file is: {}".format(options.model))
    Logger.info("throughput of normal scenario: {}".format(options.constant))
    Logger.info("throughput of burst scenario: {}".format(options.constant))
    Logger.info("window size of CM Notification: {}".format(options.window))
    Logger.info("max runtime of CM Notification: {}s".format(options.maxRuntime))
    Logger.info("debug is: {}".format(options.debug))
    Logger.info("{style}Runtime Env Prechecking{style}".format(style=style))
    runtime_env_check(home_dir, options)
    Logger.info("{style}Adaptation Updating{style}".format(style=style))
    new_model_file = ModelFile().update_metadata_version(options.model)
    Logger.info("{style}Running{style}".format(style=style))
    d = Deamon(home_dir, new_model_file, options.instance, options.constant, options.burst, options.window,
               options.maxRuntime)
    d.fork()
