#!/usr/bin/env python
# coding=utf-8
from subprocess import Popen, PIPE
import optparse
import logging
import datetime
import time
from os.path import abspath, dirname, join
import sys
import os
import traceback


class Logger(object):
    logger = logging.getLogger("Logger")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s: %(message)s')
    handler = logging.StreamHandler()
    log_file = join(dirname(abspath(__file__)), 'clean_activate_alarms.log')
    handler_f = logging.FileHandler(log_file, mode='w')
    handler.setFormatter(formatter)
    handler_f.setFormatter(formatter)
    logger.addHandler(handler)
    logger.addHandler(handler_f)

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
    command = command.strip()
    process = Popen(command, shell=True, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    stdout = stdout.decode("utf-8").strip()
    stderr = stderr.decode("utf-8").strip()
    rc = process.returncode
    if rc:
        Logger.debug("stdout: {}".format(stdout))
        Logger.debug("stderr: {}".format(stderr))
        Logger.debug("rc: {}".format(rc))
    return stdout, stderr, rc


def execute_sqlplus_command(sql, user='omc', password='omc'):
    command = 'echo -e "set head off;\\n {sql};" | sqlplus -s {user}/{password}'.format(sql=sql, user=user,
                                                                                        password=password)
    Logger.debug(sql)
    stdout, stderr, rc = execute_command(command)
    if rc and stderr:
        Logger.error(stderr)
    if stdout:
        return stdout
    return '?'


class Notification(object):
    fm_folder = '/var/opt/nokia/oss/global/mediation/south/fm/import/'
    sqlplus_user = 'omc'
    sqlplus_passwd = 'omc'

    def __init__(self, _options):
        super(Notification, self).__init__()

    def clean_activate_alarms(self):
        Logger.info("loading activate alarms")
        alarm_info_list = self.get_activate_alarm_info()
        Logger.info("clean ...")
        alarms_batch = []
        for i in range(0, len(alarm_info_list), 200):
            alarms_batch.append(alarm_info_list[i:i + 200])
        for alarm_list in alarms_batch:
            self.ack_clear_batch(alarm_list)

    def ack_clear_batch(self, alarms):
        if not alarms:
            return
        alarm_id_list = []
        contents = list()
        contents.append('<?xml version="1.0" encoding="utf-8"?>')
        contents.append('<notification>')
        for alarm in alarms:
            if not alarm:
                continue
            if len(alarm) < 4:
                continue
            alarm_id, system_dn, alarm_number, notification_id = alarm[0], alarm[1], alarm[2], alarm[3]
            alarm_id_list.append(alarm_id)
            dn = system_dn.replace('/', '%2F')
            file_name = "{fm_folder}/an_fqdn_{dn}_{notification_id}.xml.tmp".format(fm_folder=self.fm_folder, dn=dn,
                                                                                    notification_id=alarm_id)
            ack_content = """  
            <ackStateChanged systemDN="{systemDN}">
            <eventTime>{eventTime}</eventTime>
            <specificProblem>{specificProblem}</specificProblem>
            <alarmId>{alarmId}</alarmId>
            <ackStatus>acked</ackStatus>
            </ackStateChanged>""".format(systemDN=system_dn,
                                         eventTime=self.now,
                                         specificProblem=alarm_number,
                                         alarmId=notification_id).strip()
            contents.append(ack_content)
            clear_content = """   
            <alarmCleared  systemDN="{systemDN}">
            <eventTime>{eventTime}</eventTime>
            <specificProblem>{specificProblem}</specificProblem>
            <alarmId>{alarmId}</alarmId>
            </alarmCleared>""".format(systemDN=system_dn, eventTime=self.now, specificProblem=alarm_number,
                                      alarmId=notification_id).strip()
            contents.append(clear_content)
        contents.append("</notification>")
        if len(contents) <= 3:
            return
        content = "\n".join(contents)
        Logger.debug("file: {}".format(file_name))
        Logger.debug(content)
        self.send(file_name, content)
        Logger.info("clean alarmId: {} rows".format(len(alarm_id_list)))
        Logger.debug("clean alarmId: {}".format(alarm_id_list))

    @property
    def now(self):
        return datetime.datetime.now().strftime("%Y-%m-%dT%X")

    @staticmethod
    def get_activate_alarm_info():
        rows = []
        stdout = execute_sqlplus_command(
            "select CONSEC_NBR,DN,ALARM_NUMBER,NOTIFICATION_ID  from fx_alarm where ALARM_STATUS = 1 and SUPPLEMENTARY_INFO like '%pet_testalarm_warning%';\n")
        lines = list(filter(lambda line: line.strip(), stdout.split("\n")))
        lines = list(map(lambda line: line.strip(), lines))
        for i in range(0, len(lines), 4):
            rows.append(lines[i:i + 4])
        return rows

    @staticmethod
    def send(file_name, content):
        with open(file_name, 'w') as f:
            f.write(content)
        execute_command("chown omc:sysop {file} && chmod 775 {file}".format(file=file_name))
        execute_command("mv {} {}".format(file_name, file_name[:-4]))
        while 1:
            stdout, stderr, rc = execute_command("ls {}".format(file_name[:-4]))
            if rc:
                # file was consumed
                break
            time.sleep(0.1)


class Deamon(object):
    def __init__(self):
        super(Deamon, self).__init__()
        self.running = True

    def stop(self):
        self.running = False

    def fork(self):
        try:
            pid = os.fork()
        except OSError as error:
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
            except OSError as error:
                print("fork")
                sys.exit(1)
            # this is Grandson process
            self.run()
            # exit Grandson process
            sys.exit(0)
        else:
            # this is parent process . nothing to do.
            pass

    def run(self):
        while self.running:
            try:
                notify = Notification(options)
                notify.clean_activate_alarms()
                Logger.info("clean activate alarm success")
            except Exception as err:
                Logger.error("clean activate alarm failed")
                Logger.error(traceback.format_exc())
            else:
                time.sleep(300)
        Logger.info("exit")


def args_parser():
    version = '1.1'
    opt = optparse.OptionParser(version=version)
    operation_choices = ['cleanActiveAlarm']
    opt.add_option("-o", action='store', help="Mandatory,support: {}".format(operation_choices), dest="operation",
                   choices=operation_choices)
    opt.add_option("--debug", action='store_true', help="enable debug log", dest="debug")
    _options, _args = opt.parse_args()
    return _options


if __name__ == '__main__':
    options = args_parser()
    if options.debug:
        Logger.enable_debug()
    if options.operation == "cleanActiveAlarm":
        d = Deamon()
        d.fork()
