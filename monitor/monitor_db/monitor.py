#!/usr/bin/env python
# coding=utf-8
from pyinotify import WatchManager, Notifier, ProcessEvent, ALL_EVENTS
import logging
import optparse
import subprocess
import os
import sys
import traceback


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
    traceback.print_exc()
    exit(1)
else:
    # modify inotify configuration
    command = "sysctl -n -w fs.inotify.max_user_watches=999999999"
    execute_command(command)
    command = "sysctl -n -w fs.inotify.max_queued_events=999999999"
    execute_command(command)
    command = "sysctl -n -w fs.inotify.max_user_watches=999999999"
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

    @classmethod
    def error(cls, message):
        message = message.strip()
        cls.logger.error(message)


class Record(object):
    def __init__(self):
        super(Record, self).__init__()

    def record(self, file_path, message='unkown'):
        if not os.path.isfile(file_path):
            return
        result_file_size = self.get_file_size(file_path)
        Logger.info('{}, size: {}, inotify event: {}'.format(file_path.split("/")[-1], result_file_size, message))

    @staticmethod
    def get_file_size(file_path):
        try:
            if os.path.exists(file_path) and os.path.isfile(file_path):
                last_modification_time = os.path.getmtime(file_path)
                file_size = os.path.getsize(file_path)
                return '{:,} Bytes,  last modify time: {}'.format(file_size, last_modification_time)
            else:
                return 'No Exist'
        except Exception as err:
            Logger.error("{}".format(err))
            return '?'


class MyEventHandler(ProcessEvent):
    def my_init(self, **kargs):
        self.record = Record()

    def process_default(self, event):
        if event.maskname not in ['IN_ACCESS']:
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
            print('fork')
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
                print("fork error", err)
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
        wm.add_watch(self.monitor_folder, ALL_EVENTS, rec=True, auto_add=True)
        notifier = Notifier(wm, MyEventHandler())
        notifier.loop()


if __name__ == '__main__':
    opt = optparse.OptionParser()
    opt.add_option("-d", "--dictory", help="monitor this folder", dest="dictory",
                   default="/var/opt/oss/Nokia-restda-fm/leveldb/")
    options, args = opt.parse_args()
    process = Deamon(options.dictory)
    process.fork()
