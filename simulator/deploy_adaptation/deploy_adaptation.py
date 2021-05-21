import subprocess
import logging
import os
import optparse
import signal
import re
import sys


def exit_signal(sig, frame):
    Logger.info("exit by signal.")
    exit(0)


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
    # handler = logging.FileHandler(join(dirname(abspath(__file__)), 'log'))
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

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
    stdout = stdout.strip()
    stderr = stderr.strip()
    rc = process.returncode
    return stdout.decode('utf-8'), stderr.decode('utf-8'), rc


@singleton
class ModelFile(object):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.adaptation_list = []

    def load(self, model_file):
        Logger.info("load model: {}".format(model_file))
        with open(model_file, 'rb') as f:
            lines = f.readlines()
            lines = list(map(lambda line: line.decode('utf-8'), lines))
        for line in lines:
            adaptation_name = line.split(',')[0].strip()
            version = line.split(',')[1].strip()
            self.adaptation_list.append([adaptation_name, version])
        Logger.info("target adaptation: {}".format(list(map(lambda x: '/'.join(x), self.adaptation_list))))


@singleton
class AdaptationOperation(object):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.ads_client = "/opt/oss/NOKIA-integrationmanager/bin/ads_client.sh"
        self.DONE = "Deployed"
        self.STARTED = "Deploying"
        self.NOT_STARTED = "Undeployed"
        self.FAILED = "Failed"
        self.NO_EXIST = "Not exist"
        self.no_exist_adaptation_list = []
        self.not_started_adaptation_list = []
        self.started_adaptation_list = []
        self.done_adaptation_list = []
        self.failed_adaptation_list = []

    def check_adaptation_status(self, adaptation_name, version):
        command = 'runuser system -s /bin/sh -c "{ads_client} -nt {adaptation} -v {version} -q"'.format(
            ads_client=self.ads_client, adaptation=adaptation_name, version=version)
        stdout, stderr, rc = execute_command(command)
        Logger.debug(stdout)
        if "Metadata can not be found" in stdout:
            return self.NO_EXIST
        else:
            lines = stdout.split("\n")
            for line in lines:
                if "progress" in line:
                    progress = self._get_progress(line)
                    if "done" in line:
                        return self.DONE, progress
                    elif "not_started" in line:
                        return self.NOT_STARTED, progress
                    elif "started" in line:
                        return self.STARTED, progress
                    elif "failed" in line:
                        return self.FAILED, progress
                    else:
                        Logger.error("unkown status for ads_client.sh")
                        Logger.debug(stdout)
                        exit(1)

    @staticmethod
    def _get_progress(content):
        # <Status neType="NOKOMGW" neRelease="OpenMGW16.5" progress="0/3" status="not_started" totalSteps="3">
        pattern = re.compile(r'.*progress="(.*?)"', re.I)
        match = pattern.match(content)
        if match:
            return match.group(1)
        else:
            Logger.error("do not match progress")
            exit(1)

    def deploy_an_adapatation(self, adaptation_name, version):
        command = 'runuser system -s /bin/sh -c "{ads_client} -nt {adaptation} -v {version}"'.format(
            ads_client=self.ads_client, adaptation=adaptation_name, version=version)
        Logger.debug(command)
        stdout, stderr, rc = execute_command(command)
        Logger.debug(stdout)

    def check_all_adaptation_status(self, adaptation_list):
        # self.not_started_adaptation_list, self.started_adaptation_list, self.done_adaptation_list, self.failed_adaptation_list = [], [], [], []
        for adaptation in adaptation_list:
            adaptation_name = adaptation[0]
            version = adaptation[1]
            Logger.info("checking {}/{}".format(adaptation_name, version))
            status, progress = self.check_adaptation_status(adaptation_name, version)
            if status == self.NO_EXIST:
                self.no_exist_adaptation_list.append(adaptation)
            elif status == self.NOT_STARTED:
                self.not_started_adaptation_list.append([adaptation_name, version, progress])
            elif status == self.STARTED:
                self.started_adaptation_list.append([adaptation_name, version, progress])
            elif status == self.DONE:
                adaptation.append(progress)
                self.done_adaptation_list.append([adaptation_name, version, progress])
            elif status == self.FAILED:
                adaptation.append(progress)
                self.failed_adaptation_list.append([adaptation_name, version, progress])
        Logger.info("*" * 50)
        Logger.info("Undeployed: {}".format(list(map(lambda x: ':'.join(x), self.not_started_adaptation_list))))
        Logger.info("Deploying: {}".format(list(map(lambda x: ':'.join(x), self.started_adaptation_list))))
        Logger.info("Deployed: {}".format(list(map(lambda x: ':'.join(x), self.done_adaptation_list))))
        Logger.info("NotExist: {}".format(list(map(lambda x: ':'.join(x), self.no_exist_adaptation_list))))
        Logger.info("DepolyFailed: {}".format(list(map(lambda x: ':'.join(x), self.failed_adaptation_list))))
        Logger.info("*" * 50)

    def deploy(self):
        for adaptation in self.not_started_adaptation_list:
            adaptation_name = adaptation[0]
            version = adaptation[1]
            Logger.info("deploying {}:{}".format(adaptation_name, version))
            self.deploy_an_adapatation(adaptation_name, version)
            Logger.info("deployed {}:{}".format(adaptation_name, version))
        for adaptation in self.failed_adaptation_list:
            adaptation_name = adaptation[0]
            version = adaptation[1]
            Logger.info("deploying {}:{}".format(adaptation_name, version))
            self.deploy_an_adapatation(adaptation_name, version)
            Logger.info("deployed {}:{}".format(adaptation_name, version))
        Logger.info("all exist adaptation are deployed.")


class Deamon(object):
    def __init__(self):
        super(Deamon, self).__init__()
        self.running = True

    def stop(self):
        self.running = False

    def fork(self):
        try:
            pid = os.fork()
        except OSError as err:
            print('fork error: {}'.format(str(err)))
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
                print('fork error: {}'.format(str(err)))
                sys.exit(1)
            # this is Grandson process
            self.run()
            # exit Grandson process
            sys.exit(0)
        else:
            # this is parent process . nothing to do.
            pass

    @staticmethod
    def run():
        AdaptationOperation().check_all_adaptation_status(ModelFile().adaptation_list)
        AdaptationOperation().deploy()


if __name__ == "__main__":
    # /var/opt/oss/global/NSN-integrationmanager/adaptationStorage/
    signal.signal(signal.SIGINT, exit_signal)
    opt = optparse.OptionParser(version="1.0")
    opt.add_option("--debug", help="enable debug", action='store_true', dest="debug")
    opt.add_option("--model", help="model file, default: adaptation.csv", default='adaptation.csv', dest='model')
    opt.add_option("--check", help="check adaptation status from adaptation.csv", action='store_true', dest='check')
    opt.add_option("--deploy", help="deploy adaptation status from adaptation.csv", action='store_true', dest='deploy')
    options, args = opt.parse_args()
    HOME_DIR = os.path.dirname(os.path.abspath(__file__))
    if options.debug:
        Logger.enable_debug()
    if not (os.path.exists(options.model) and os.path.isfile(options.model)):
        Logger.error("model: {} is not exist.".format(options.model))
        exit(1)
    if not (os.path.exists(AdaptationOperation().ads_client) and os.path.isfile(AdaptationOperation().ads_client)):
        Logger.error("tool: {} is not exist. please log in dmgr node".format(AdaptationOperation().ads_client))
        exit(1)
    ModelFile().load(options.model)
    if options.check:
        AdaptationOperation().check_all_adaptation_status(ModelFile().adaptation_list)
    elif options.deploy:
        d = Deamon()
        d.fork()
