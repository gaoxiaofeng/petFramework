import subprocess
import logging
import os
import optparse
import time
from threading import Thread, Lock
import signal
import re
import sys


def exit_signal(sig, frame):
    global worker_thread_list, master_thread_list
    for worker_thread in worker_thread_list:
        worker_thread.stop()
    for master_thread in master_thread_list:
        master_thread.stop()


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
    handler_file = logging.FileHandler('import_objects.log', mode='w')
    handler_stream = logging.StreamHandler()
    handler_file.setFormatter(formatter)
    handler_stream.setFormatter(formatter)
    logger.addHandler(handler_file)
    logger.addHandler(handler_stream)

    @classmethod
    def _convert(cls, message):
        message = str(message)
        message = message.strip()
        return message

    @classmethod
    def info(cls, message):
        message = cls._convert(message)
        cls.logger.info(message)

    @classmethod
    def error(cls, message):
        message = cls._convert(message)
        cls.logger.error(message)

    @classmethod
    def debug(cls, message):
        message = cls._convert(message)
        cls.logger.debug(message)

    @classmethod
    def warning(cls, message):
        message = cls._convert(message)
        cls.logger.warning(message)

    @classmethod
    def enable_debug(cls):
        cls.logger.setLevel(logging.DEBUG)


def execute_command(command):
    command = command.strip()
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    stdout = stdout.decode("utf-8").strip()
    stderr = stderr.decode("utf-8").strip()
    rc = process.returncode
    return stdout, stderr, rc


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

    def search_lab_metadata(self, use_oldest_metadata=False, usemainstreammetadata=False):
        Logger.info("search metadata in lab.")
        for metadata_name in self.need_updated_metadata:
            metadata_list = self.get_metadata_version(metadata_name, exclude='5G')
            if use_oldest_metadata:
                selected_metadata = metadata_list[0]
            elif usemainstreammetadata:
                if len(metadata_list) >= 5:
                    selected_metadata = metadata_list[-2]
                else:
                    selected_metadata = metadata_list[-1]
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
            dn = _line[0]
            args = _line[-1].replace(";", ",")
            _args = eval(args)
            metadata = _args["$version"]
            metadata_set.update({metadata})
        for metadata_name in self.need_updated_metadata:
            metadata = self._get_matched_metadata(metadata_set, metadata_name)
            if metadata:
                self.model_file_map.update({metadata_name: metadata})
                Logger.info("model file-> {}: {}".format(metadata_name, metadata))

    @staticmethod
    def _get_matched_metadata(metadata_set, metadata_name):
        for metadata in metadata_set:
            if metadata.startswith(metadata_name):
                return metadata
        Logger.warning("metadata set {} has not metadata: {}".format(metadata_set, metadata_name))
        return None

    def update_metadata_version(self, model_file, use_oldest_metadata=False, usemainstreammetadata=False):
        new_model_file = os.path.join(os.path.dirname(model_file), ".{}".format(model_file.split("/")[-1]))
        self.search_model_metadata(model_file)
        self.search_lab_metadata(use_oldest_metadata, usemainstreammetadata)
        self._update_metadata_version(model_file, new_model_file)
        return new_model_file

    def _update_metadata_version(self, model_file, new_model_file):
        Logger.info("update metadata and save to file: {}".format(new_model_file))
        with open(model_file, "rb") as f:
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

        with open(new_model_file, "wb") as f:
            f.write("\n".join(new_lines).encode("utf-8"))


@singleton
class ImportMo(object):
    def __init__(self):
        self._lbwas = ""

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

    def import_mo(self, file_path, monkey):
        start_time = time.time()
        command = "java -jar /home/omc/manageObjectSim.jar --ip {} --file {}".format(self.lbwas, file_path)
        Logger.debug(command)
        stdout, stderr, rc = execute_command(command)
        end_time = time.time()
        Logger.debug("stdout: {}".format(stdout))
        Logger.debug("stderr: {}".format(stderr))
        if not monkey and (rc or 'error' in stdout.lower() or 'error' in stderr.lower()):
            Logger.error("rc: {}".format(rc))
            Logger.error("stdout: {}".format(stdout))
            Logger.error("stderr: {}".format(stderr))
            raise Exception(stderr)
        return end_time - start_time


def sort_by_number(name):
    return int(name.split("_")[-1].split(".")[0])


def list_configration(home_dir, file_prefix):
    files = []
    for file_name in os.listdir(home_dir):
        if file_name.startswith(file_prefix):
            file_path = os.path.join(home_dir, file_name)
            files.append(file_path)
    files.sort(key=sort_by_number)
    return files


def get_mrbts(instance):
    dn_list = []
    command = """
    echo -e "set head off;\n set linesize 2000;\n select co_dn from ctp_common_objects where co_dn like '%MRBTS-%{INSTANCE}%' and co_dn not like '%MRBTS-%{INSTANCE}%/%';"| sqlplus omc/omc
    """.format(INSTANCE=instance).strip()
    stdout, stderr, rc = execute_command(command)
    for line in stdout.split("\n"):
        dn_list.append(line.strip())
    return dn_list


content_head = """<operation type="add" xmlns="http://operation.test.nbi.oss.nsn.com">\n\t<networkElements>"""
content_tail = """\n\t</networkElements>\n</operation>"""
attr_template = "<property><name>{attr}</name><value>{value}</value></property>"
default_mo_template = """<networkElement dn="{dn}"><rac clazz="{clazz}" version="{version}">{attrs}</rac></networkElement>"""
mrbts_mo_template = """<networkElement dn="{dn}"><rac clazz="{clazz}" version="{version}">{attrs}</rac><nasda clazz="com.nsn.netact.nasda.connectivity:MRBTS" version="1.0"><property><name>name</name><value>{nasda_name}</value></property></nasda></networkElement>"""
plmn_template = """<networkElement dn="PLMN-{plmn_name}"><nasda clazz="com.nsn.netact.nasda.connectivity:PLMN" version="1.0"></nasda></networkElement>"""


class Worker(Thread):
    def __init__(self, xml_dir, file_prefix, lock, monkey, manager_thread):
        super(Worker, self).__init__()
        self.xml_dir = xml_dir
        self.file_prefix = file_prefix
        self.lock = lock
        self.monkey = monkey
        self.manager_thread = manager_thread
        self.running = True

    def run(self):
        while 1:
            if not self.running:
                break
            self.lock.acquire()
            configuration_list = list_configration(self.xml_dir, self.file_prefix)
            if configuration_list:
                file_path = configuration_list[0]
                locked_file_name = 'locked_{}'.format(file_path.split("/")[-1])
                locked_file_path = os.path.join(self.xml_dir, locked_file_name)
                failed_file_name = 'failed_{}'.format(file_path.split("/")[-1])
                failed_file_path = os.path.join(self.xml_dir, failed_file_name)
                os.rename(file_path, locked_file_path)
                self.lock.release()
                try:
                    cost = ImportMo().import_mo(locked_file_path, self.monkey)
                except Exception as err:
                    if 'HTTP transport error' in str(err):
                        Logger.error("Network issue, sleep 60 and go on.")
                        os.rename(locked_file_path, failed_file_path)
                        time.sleep(60)
                        continue
                    else:
                        Logger.error("Worker Exception Occur")
                        break
                else:
                    os.remove(locked_file_path)
                    Logger.info("imported {}, cost: {}s".format(file_path, cost))
            else:
                self.lock.release()
                if not self.manager_thread.is_alive():
                    break
                time.sleep(1)

    def stop(self):
        self.running = False


class Master(Thread):
    def __init__(self, xml_dir, file_prefix, mrbts_count, mrbts_instance, model_file, bare, batch, worker_count):
        super(Master, self).__init__()
        self.xml_dir = xml_dir
        self.file_prefix = file_prefix
        self.mrbts_count = mrbts_count
        self.mrbts_instance = mrbts_instance
        self.model_file = model_file
        self.bare = bare
        self.batch = batch
        self.worker_count = worker_count
        self.running = True

    def run(self):
        configuration_list = list_configration(self.xml_dir, self.file_prefix)
        Logger.info("Legacy configurations: [{}]".format(len(configuration_list)))
        if not configuration_list:
            Logger.info("start generate configuration.")
            self.generate_configuration()

    def stop(self):
        self.running = False

    def generate_configuration(self):
        exist_mrbts_list = get_mrbts(self.mrbts_instance)
        file_no = 0
        for mrbts_id in range(1, self.mrbts_count + 1):
            while 1:
                if not self.running:
                    break
                if len(list_configration(self.xml_dir, self.file_prefix)) > self.worker_count * 3:
                    time.sleep(2)
                else:
                    break
            if not self.running:
                break
            mrbts_name = "{}{}".format(self.mrbts_instance, mrbts_id)
            mrbts_path = 'PLMN-PLMN/MRBTS-{}'.format(mrbts_name)
            if mrbts_path in exist_mrbts_list:
                Logger.info("{} already exist, next.".format(mrbts_path))
                continue
            network_elements = self.generate_mo_by_model(mrbts_name)
            for batch_id in range(int(len(network_elements) / self.batch) + 1):
                file_no += 1
                network_elements_batch = network_elements[batch_id * self.batch:batch_id * self.batch + self.batch]
                file_path = "{}/{}_{}_fileno_{}.xml".format(self.xml_dir, self.file_prefix, mrbts_name, file_no)
                with open(file_path, "wb") as f:
                    f.write(content_head.encode("utf-8"))
                    f.write('\n'.join(network_elements_batch).encode("utf-8"))
                    f.write(content_tail.encode("utf-8"))
                Logger.info("generated {}".format(file_path))

    def generate_mo_by_model(self, mrbts_name):
        model = self.init_model()
        network_elements = list()
        network_elements.append(plmn_template.format(plmn_name="PLMN"))
        for row in model:
            dn_name = row.split(",")[0].format(MRBTSID=mrbts_name)
            attrs = eval(row.split(",")[1].replace(";", ","))
            version = attrs.pop("$version")
            clazz = attrs.pop("$class")
            attrs_string_list = []
            for attr_name in attrs:
                if not attr_name.startswith("$"):
                    if ":" in attr_name:
                        Logger.debug("Mo: {}, attr: {} , ignore".format(dn_name, attr_name, attrs[attr_name]))
                    else:
                        if not self.bare:
                            attr_value = attrs[attr_name].format(MRBTSID=mrbts_name)
                            attrs_string_list.append(attr_template.format(attr=attr_name, value=attr_value))
            if self._is_mrbts(dn_name):
                nasda_name = mrbts_name.upper()
                mo_string = mrbts_mo_template.format(dn=dn_name, version=version, clazz=clazz,
                                                     attrs="".join(attrs_string_list), nasda_name=nasda_name)
            else:
                mo_string = default_mo_template.format(dn=dn_name, version=version, clazz=clazz,
                                                       attrs="".join(attrs_string_list))
            network_elements.append(mo_string)
        return network_elements

    @staticmethod
    def _is_mrbts(dn):
        mrbts_pattern = re.compile(r".*MRBTS[^/]+$", re.I)
        return True if mrbts_pattern.match(dn) else False

    def init_model(self):
        with open(self.model_file, "rb") as f:
            lines = f.readlines()
            lines = list(map(lambda line: line.decode('utf-8'), lines))
        return lines


class Deamon(object):
    def __init__(self, modle_file, useoldestmetadata,usemainstreammetadata, mrbtscount, instance, bare, batch, thread, monkey):
        super(Deamon, self).__init__()
        self.running = True
        self.modle_file = modle_file
        self.useoldestmetadata = useoldestmetadata
        self.usemainstreammetadata = usemainstreammetadata
        self.mrbtscount = mrbtscount
        self.instance = instance
        self.bare = bare
        self.batch = batch
        self.thread = thread
        self.monkey = monkey

    def stop(self):
        self.running = False

    def fork(self):
        try:
            pid = os.fork()
        except OSError as error:
            Logger.error('fork error: {}'.format(error))
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
            except OSError as error:
                Logger.error('fork error: {}'.format(error))
                sys.exit(1)
            # this is Grandson process
            self.run()
            # exit Grandson process
            sys.exit(0)
        else:
            # this is parent process . nothing to do.
            pass

    def run(self):
        import_cm_objects(self.modle_file, self.useoldestmetadata, self.usemainstreammetadata, self.mrbtscount, self.instance, self.bare, self.batch,
                          self.thread, self.monkey)


def args_precheck():
    opt = optparse.OptionParser(version="1.0")
    opt.add_option("--debug", help="enable debug", action='store_true', dest="debug")
    opt.add_option("--instance", help="instance of mrbts, default: restda, will create PLMN-PLMN/MRBTS-restda<id>", default='restda', dest='instance')
    opt.add_option("--mrbtscount", help="count of PLMN/MRBTS, default: 1, max: 10000", default=1, type=int,
                   dest='mrbtscount')
    opt.add_option("--modelfile", help="model file", dest='modelfile')
    opt.add_option("--batch", help="count of batch, default: 10000", default=10000, dest='batch', type=int)
    opt.add_option("--thread", help="count of thread, default: 1", default=1, dest='thread', type=int)
    opt.add_option("--bare", help="create mo without attribute", action='store_true', dest='bare')
    opt.add_option("--useoldestmetadata", help="use oldest metadata", action='store_true', dest='useoldestmetadata')
    opt.add_option("--usemainstreammetadata", help="use mainstream metadata", action='store_true', dest='usemainstreammetadata')
    opt.add_option("--monkey", help="ignore error", action='store_true', dest='monkey')
    opt.add_option("--precheck", help="has not metadata model", action='store_true', dest='precheck')
    options, args = opt.parse_args()
    if options.debug:
        Logger.enable_debug()
    if not options.modelfile:
        Logger.error("--modelfile: is missing".format(options.modelfile))
        exit(1)
    if not os.path.isabs(options.modelfile):
        Logger.error("model: {} is not abs path.".format(options.modelfile))
        exit(1)
    if not (os.path.exists(options.modelfile) and os.path.isfile(options.modelfile)):
        Logger.error("model: {} is not exist.".format(options.modelfile))
        exit(1)
    if not (os.path.exists("/home/omc/manageObjectSim.jar") and os.path.isfile("/home/omc/manageObjectSim.jar")):
        Logger.error("/home/omc/manageObjectSim.jar is not exist, you can copy it from nbi3gc")
        exit(1)
    if not (os.path.exists(ModelFile().metadata_home) and os.path.isdir(ModelFile().metadata_home)):
        Logger.error("metadata folder {} is not exist.".format(ModelFile().metadata_home))
        exit(1)
    if options.precheck:
        ModelFile().update_metadata_version(options.modelfile, options.useoldestmetadata)
        Logger.info("precheck model done.")
        exit(0)
    return options, args


def import_cm_objects(model_file, useoldestmetadata, usemainstreammetadata, mrbts_count, instance, bare, batch, thread, monkey):
    global worker_thread_list, master_thread_list
    new_model_file = ModelFile().update_metadata_version(model_file, useoldestmetadata, usemainstreammetadata)
    home_dir = os.path.dirname(os.path.abspath(__file__))
    xml_dir = os.path.join(home_dir, "MO_XML")
    file_prefix = "create_lte_by_script"
    if not os.path.exists(xml_dir):
        os.mkdir(xml_dir)
    starttime = time.time()
    lock = Lock()
    master_thread = Master(xml_dir, file_prefix, mrbts_count, instance, new_model_file,
                           bare, batch, thread)

    master_thread.start()
    master_thread_list.append(master_thread)
    Logger.info("master threading-0 started.")

    worker_thread_list = []
    for i in range(thread):
        worker_thread = Worker(xml_dir, file_prefix, lock, monkey, master_thread)
        worker_thread_list.append(worker_thread)
    for index, worker_thread in enumerate(worker_thread_list):
        worker_thread.start()
        Logger.info("worker threading-{} started.".format(index + 1))
    while 1:
        status = [worker_thread.is_alive() for worker_thread in worker_thread_list]
        if not any(status):
            Logger.info("all workers are exit.")
            break
        time.sleep(1)
    for worker_thread in worker_thread_list:
        worker_thread.stop()
    for master_thread in master_thread_list:
        master_thread.stop()
    endtime = time.time()
    Logger.info("total cost: {}s".format(endtime - starttime))


if __name__ == "__main__":
    global worker_thread_list, master_thread_list
    worker_thread_list, master_thread_list = [], []
    signal.signal(signal.SIGINT, exit_signal)
    options, args = args_precheck()
    process = Deamon(options.modelfile, options.useoldestmetadata, options.usemainstreammetadata, options.mrbtscount, options.instance, options.bare,
                     options.batch, options.thread, options.monkey)
    process.fork()
