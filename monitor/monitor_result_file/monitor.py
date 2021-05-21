#!/usr/bin/env python
# coding=utf-8
from pyinotify import WatchManager, Notifier, ProcessEvent, IN_CREATE, IN_DELETE, IN_MODIFY, IN_MOVED_FROM, IN_MOVED_TO
import logging
import optparse
import subprocess
import os
import sys


def execute_command(command):
    command = command.strip()
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout = process.stdout.read()
    stdout = stdout.strip()
    stderr = process.stderr.read()
    stderr = stderr.strip()

    return stdout.decode('utf-8'), stderr.decode('utf-8')


try:
    command = "grep INOTIFY_USER /boot/config-$(uname -r)"
    stdout, stderr = execute_command(command)
    if stdout and '=' in stdout and stdout.split('=')[1].lower() == 'y':
        pass
    else:
        print('the Linux kernel Not Support Inotify')
        exit(1)
except Exception as err:
    print(err)
    exit(1)
else:
    # modify inotify configuration
    command = "sysctl -n -w fs.inotify.max_user_watches=10000000"
    execute_command(command)


class Logger(object):
    logger = logging.getLogger("Debug")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s : %(message)s')
    handler = logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Monitor.log'))
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    @classmethod
    def info(cls, message):
        message = message.strip()
        cls.logger.info(message)


class Record(object):
    def __init__(self):
        super(Record, self).__init__()

    def record(self, result_file, message='unkown'):
        if not os.path.isfile(result_file):
            return
        result_file_size = self.get_file_size(result_file)
        result_file_rows_count = self.get_file_rows_count(result_file)
        Logger.info('{},{},{}:{}'.format(result_file, result_file_rows_count, result_file_size, message))

    @staticmethod
    def get_file_size(result_file):
        try:
            command = 'wc -c {}'.format(result_file)
            stdout, stderr = execute_command(command)
            size = int(stdout.split(' ')[0])
        except Exception as err:
            return '?'
        else:
            return size

    @staticmethod
    def get_file_rows_count(result_file):
        try:
            command = 'zcat {} | wc -l'.format(result_file)
            stdout, stderr = execute_command(command)
            rows_count = int(stdout.split(' ')[0])
            if rows_count > 0:
                # ignore first row
                rows_count -= 1
            else:
                return None
        except Exception as err:
            return '?'
        else:
            return rows_count


class MyEventHandler(ProcessEvent):
    def my_init(self, **kargs):
        self.record = Record()

    def process_IN_CREATE(self, event):  # create new file
        self._process(event)

    # def process_IN_DELETE(self, event):  # delete file,such as rm
    #     self._process(event)

    def process_IN_MODIFY(self, event):  # modify file content
        self._process(event)

    def process_IN_MOVED_FROM(self, event):  # where file move from ，such as mv
        self._process(event)

    def process_IN_MOVED_TO(self, event):  # where file move to,such as mv，cp
        self._process(event)

    def _process(self, event):
        self.record.record(os.path.join(event.path, event.name), message=event.maskname)


class Deamon(object):
    def __init__(self, monitor_folder):
        super(Deamon, self).__init__()
        self.running = True
        self.monitor_folder = monitor_folder

    def stop(self):
        self.running = False

    def fork(self):
        try:
            pid = os.fork()
        except OSError as err:
            print('fork err: ', err)
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
                print("fork err: ", err)
                sys.exit(1)
            # this is Grandson process
            self.run()
            # exit Grandson process
            sys.exit(0)
        else:
            # this is parent process . nothing to do.
            pass

    def run(self):
        wm = WatchManager()
        mask = IN_CREATE | IN_DELETE | IN_MODIFY | IN_MOVED_FROM | IN_MOVED_TO
        wm.add_watch(self.monitor_folder, mask, rec=True, auto_add=True)
        notifier = Notifier(wm, MyEventHandler())
        notifier.loop()


if __name__ == '__main__':
    opt = optparse.OptionParser()
    opt.add_option("-d", "--dictory", help="monitor this folder", dest="dictory", default="/var/opt/oss/restda/result")
    options, args = opt.parse_args()
    process = Deamon(options.dictory)
    process.fork()

    # wm = WatchManager()
    # mask = IN_CREATE | IN_DELETE | IN_MODIFY | IN_MOVED_FROM | IN_MOVED_TO
    # wm.add_watch(MONITOR_DIR, mask, rec=True, auto_add=True)
    #
    # notifier = Notifier(wm, MyEventHandler())
    # notifier.loop()
