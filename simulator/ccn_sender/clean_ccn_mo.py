import subprocess
import logging
import os
import optparse
import time
from threading import Thread, Lock

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


def executeCommand(command):
    command = command.strip()
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
    stdout, stderr = process.communicate()
    stdout = stdout.strip()
    stderr = stderr.strip()
    rc = process.returncode
    return stdout, stderr, rc


@singleton
class DeleteMo(object):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'deleting_cache')
        self.ractoolsmx = "/opt/oss/NSN-cmplatform/bin/ractoolsmx.sh"
        if not (os.path.exists(self.cache_file) and os.path.isfile(self.cache_file)):
            with open(self.cache_file, "wb") as f:
                pass

    def check_tool(self):
        if not (os.path.exists(self.ractoolsmx) and os.path.isfile(self.ractoolsmx)):
            Logger.error(" script is only running on was node!")
            exit(1)

    def delete_mo(self, mo_name):
        command = "{} -objmgr -remove {}".format(self.ractoolsmx, mo_name)
        stdout, stderr, rc = executeCommand(command)
        if rc or stderr or 'error' in stdout.lower():
            Logger.error(stdout)
            exit(1)

    def getMrbts(self, prefix):
        dn_list = []
        command = """
        echo -e "set head off;\n set linesize 2000;\n select co_dn from ctp_common_objects where co_dn like '%MRBTS-{PREFIX}%' and co_dn not like '%MRBTS-{PREFIX}%/%';"| sqlplus omc/omc |grep PLMN-PLMN
        """.format(PREFIX=prefix).strip()
        stdout, stderr, rc = executeCommand(command)
        for line in stdout.split("\n"):
            dn_list.append(line.strip())
        return dn_list

    @property
    def lock(self):
        with open(self.cache_file, "rb") as f:
            lines = f.readlines()
        return list(map(lambda line: line.strip(), lines))

    @lock.setter
    def lock(self, mo_name):
        with open(self.cache_file, "ab") as f:
            f.write("{}\n".format(mo_name).encode('utf-8'))


class Deleting(Thread):
    def __init__(self, lock):
        super(Deleting, self).__init__()
        self.lock = lock

    def run(self):
        dn_list = DeleteMo().getMrbts(options.prefix)
        Logger.info("{} Mo deleting...".format(len(dn_list)))
        for index, dn_name in enumerate(dn_list):
            self.lock.acquire()
            deleted_mo_list = DeleteMo().lock
            self.lock.release()
            if dn_name not in deleted_mo_list:
                self.lock.acquire()
                DeleteMo().lock = dn_name
                self.lock.release()
                DeleteMo().delete_mo(dn_name)
                Logger.info("deleted {}: {}/{}".format(dn_name, index + 1, len(dn_list)))




if __name__ == "__main__":
    opt = optparse.OptionParser(version="1.0")
    opt.add_option("--prefix", help="prefix of mrbts, default: Notifier", default='Notifier', dest='prefix')
    opt.add_option("--thread", help="thread count, default: 1", default=1, type=int, dest='thread')
    options, args = opt.parse_args()
    DeleteMo().check_tool()
    global_lock = Lock()
    thread_list = []
    for i in range(options.thread):
        t = Deleting(global_lock)
        thread_list.append(t)
    for t in thread_list:
        t.start()
    for t in thread_list:
        t.join()





