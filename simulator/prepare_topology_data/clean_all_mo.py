import subprocess
import logging
import os
import optparse


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
    Logger.debug(command)
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    stdout = stdout.decode('utf-8', errors="ignore").strip()
    stderr = stderr.decode('utf-8', errors="ignore").strip()
    rc = process.returncode
    Logger.debug("stdout: {}".format(stdout))
    Logger.debug("stderr: {}".format(stderr))
    Logger.debug("rc: {}".format(rc))
    return stdout, stderr, rc


@singleton
class DeleteMo(object):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.ractoolsmx = "/opt/oss/NSN-cmplatform/bin/ractoolsmx.sh"
        self.nasdaclimx = "/opt/oss/NSN-nasda-platform/bin/nasdaclimx.sh"
        self._cm_mo_list = []
        self._nasda_mo_list = []

    def check_tool(self):
        if not (os.path.exists(self.ractoolsmx) and os.path.isfile(self.ractoolsmx)):
            Logger.error("tool: {} is not exist, script is only running on was node!".format(self.ractoolsmx))
            exit(1)
        if not (os.path.exists(self.nasdaclimx) and os.path.isfile(self.nasdaclimx)):
            Logger.error("tool: {} is not exist, script is only running on was node!".format(self.nasdaclimx))
            exit(1)

    def clean_all_mo(self, include):
        for mo_name in self.nasda_mo_list:
            if include:
                if include in mo_name:
                    self.delete_nasda_mo(mo_name)
            else:
                self.delete_nasda_mo(mo_name)
        for mo_name in self.cm_mo_list:
            if include:
                if include in mo_name:
                    self.delete_cm_mo(mo_name)
            else:
                self.delete_cm_mo(mo_name)

    def get_all_mo(self, include):
        for mo_name in self.nasda_mo_list:
            if include:
                if include in mo_name:
                    Logger.info("NASDA: {}".format(mo_name))
            else:
                Logger.info("NASDA: {}".format(mo_name))
        for mo_name in self.cm_mo_list:
            if include:
                if include in mo_name:
                    Logger.info("CM: {}".format(mo_name))
            else:
                Logger.info("CM: {}".format(mo_name))

    def delete_cm_mo(self, mo_name):
        command = "{} -objmgr -remove {}".format(self.ractoolsmx, mo_name)
        stdout, stderr, rc = execute_command(command)
        if rc or stderr or 'error' in stdout.lower():
            Logger.error(stdout)
            exit(1)
        else:
            Logger.info("deleted: {} for cm".format(mo_name))

    def delete_nasda_mo(self, mo_name):
        command = "{} -objmgr -remove {}".format(self.nasdaclimx, mo_name)
        stdout, stderr, rc = execute_command(command)
        if rc or stderr or 'error' in stdout.lower():
            Logger.error(stdout)
            exit(1)
        else:
            Logger.info("deleted: {} for nasda".format(mo_name))

    @property
    def cm_mo_list(self):
        if not self._cm_mo_list:
            self._cm_mo_list = self.get_mo_objects("ctp_common_objects")
        Logger.debug("exist cm objects: {}".format(self._cm_mo_list))
        return self._cm_mo_list

    @staticmethod
    def get_mo_objects(tablename):
        dn_list = []
        command = """
        echo -e "set head off;\n set linesize 2000;\n select co_dn from {table} where co_dn not like '%/%';"| sqlplus omc/omc
        """.format(table=tablename)
        stdout, stderr, rc = execute_command(command)
        mo_start_flag = False
        for line in stdout.split("\n"):
            mo_name = line.strip()
            if "SQL>" in mo_name:
                mo_start_flag = True
                continue
            if mo_start_flag and mo_name and " " not in mo_name:
                dn_list.append(mo_name)
        return dn_list

    @property
    def nasda_mo_list(self):
        if not self._nasda_mo_list:
            self._nasda_mo_list = self.get_mo_objects("nasda_objects")
        Logger.debug("exist nasda objects: {}".format(self._nasda_mo_list))
        return self._nasda_mo_list


if __name__ == "__main__":
    opt = optparse.OptionParser(version="1.0")
    opt.add_option("--debug", action='store_true', help="debug level", dest="debug")
    opt.add_option("--include", help="if not use, delete all mo in cm and nasda table", dest="include")
    opt.add_option("--delete", action='store_true', help="if not use, print the mo list which can be deleted", dest="delete")
    options, args = opt.parse_args()
    if options.debug:
        Logger.enable_debug()
    DeleteMo().check_tool()
    if options.delete:
        DeleteMo().clean_all_mo(options.include)
    else:
        DeleteMo().get_all_mo(options.include)