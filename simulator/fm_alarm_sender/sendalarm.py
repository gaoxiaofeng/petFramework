#!/usr/bin/env python
# coding=utf-8
import re
from subprocess import Popen, PIPE
import time
import os
import optparse
import logging
import datetime


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
    command = command.strip()
    process = Popen(command, shell=True, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    stdout = stdout.strip()
    stderr = stderr.strip()
    rc = process.returncode
    if rc:
        Logger.debug("stdout: {}".format(stdout))
        Logger.debug("stderr: {}".format(stderr))
        Logger.debug("rc: {}".format(rc))
    return stdout, stderr, rc


class Notification(object):
    fm_folder = '/var/opt/nokia/oss/global/mediation/south/fm/import/'
    sqlplus_user = 'omc'
    sqlplus_passwd = 'omc'

    def __init__(self, _options):
        super(Notification, self).__init__()
        self.consecNbr = _options.consecNbr
        self.DN = _options.dn
        self.specificProblem = _options.specificProblem
        self.notificationId = _options.notificationId
        self.perceivedSeverity = _options.perceivedSeverity
        self.eventType = _options.eventType
        self.alarmText = _options.alarmText
        self.additionalText1 = _options.additionalText1
        self.additionalText2 = _options.additionalText2
        self.additionalText3 = _options.additionalText3
        self.additionalText4 = _options.additionalText4
        self.additionalText5 = _options.additionalText5
        self.additionalText6 = _options.additionalText6
        self.additionalText7 = _options.additionalText7
        self.eventTime = _options.eventTime

    def clear(self):
        self.DN, self.specificProblem, self.notificationId = self.get_alarm_info()
        if 'SDM' in self.DN:
            # SDM
            self.dnstr = self.DN.split('/')[0] + '%2F' + self.DN.split('/')[1]
            self.DN = self.DN[self.DN.index("SDM"):]
        else:
            self.dnstr = self.DN.replace('/', '%2F')
        self.fileName = self.fm_folder + 'an_fqdn_' + self.dnstr + '_' + self.notificationId + '.xml.tmp'
        s = '<?xml version="1.0"?>\n'
        s += '<notification>\n' + '\t'
        s += '<alarmCleared  systemDN="' + self.DN + '">' + '\n' + '\t' + '\t'
        s += '<eventTime>' + str(self.now) + '</eventTime>' + '\n' + '\t' + '\t'
        s += '<specificProblem>' + self.specificProblem + '</specificProblem>' + '\n' + '\t' + '\t'
        s += '<alarmId>' + self.notificationId + '</alarmId>' + '\n' + '\t' + '\t'
        s += '</alarmCleared>' + '\n'
        s += '</notification>\n'
        self.content = s
        Logger.debug(self.content)
        self.send()
        Logger.info("clear alarm success!")
        Logger.info("alarmId: {}".format(self.consecNbr))

    def change_alarm(self):
        self.DN, self.specificProblem, self.notificationId = self.get_alarm_info()
        if 'SDM' in self.DN:
            # SDM
            self.dnstr = self.DN.split('/')[0] + '%2F' + self.DN.split('/')[1]
            self.DN = self.DN[self.DN.index("SDM"):]
        else:
            self.dnstr = self.DN.replace('/', '%2F')
        self.fileName = self.fm_folder + 'an_fqdn_' + self.dnstr + '_' + self.notificationId + '.xml.tmp'
        s = '<?xml version="1.0"?>\n'
        s += '<notification>\n' + '\t'
        s += '<alarmChanged systemDN="' + self.DN + '">' + '\n' + '\t' + '\t'
        s += '<alarmId>' + self.notificationId + '</alarmId>' + '\n' + '\t' + '\t'
        s += '<eventTime>' + str(self.now) + '</eventTime>' + '\n' + '\t' + '\t'
        s += '<specificProblem>' + self.specificProblem + '</specificProblem>' + '\n' + '\t' + '\t'
        s += '<alarmText>' + self.alarmText + '</alarmText>' + '\n' + '\t' + '\t'
        s += '<perceivedSeverity>' + self.perceivedSeverity + '</perceivedSeverity>' + '\n' + '\t' + '\t'
        s += '<additionalText1>' + self.additionalText1 + '</additionalText1>' + '\n' + '\t' + '\t'
        s += '<additionalText2>' + self.additionalText2 + '</additionalText2>' + '\n' + '\t' + '\t'
        s += '<additionalText3>' + self.additionalText3 + '</additionalText3>' + '\n' + '\t' + '\t'
        s += '<additionalText4>' + self.additionalText4 + '</additionalText4>' + '\n' + '\t' + '\t'
        s += '<additionalText5>' + self.additionalText5 + '</additionalText5>' + '\n' + '\t' + '\t'
        s += '<additionalText6>' + self.additionalText6 + '</additionalText6>' + '\n' + '\t' + '\t'
        s += '<additionalText7>' + self.additionalText7 + '</additionalText7>' + '\n' + '\t' + '\t'
        s += '<eventType>' + self.eventType + '</eventType>' + '\n' + '\t'
        s += '</alarmChanged>' + '\n'
        s += '</notification>\n'
        self.content = s
        Logger.debug(self.content)
        self.send()
        Logger.info("change alarm success!")
        Logger.info("alarmId: {}".format(self.consecNbr))

    def ackalarm(self):
        operation = "acked" if options.operation == "ack" else "unacked"
        self.DN, self.specificProblem, self.notificationId = self.get_alarm_info()
        if 'SDM' in self.DN:
            # SDM
            self.dnstr = self.DN.split('/')[0] + '%2F' + self.DN.split('/')[1]
            self.DN = self.DN[self.DN.index("SDM"):]
        else:
            self.dnstr = self.DN.replace('/', '%2F')
        self.fileName = self.fm_folder + 'an_fqdn_' + self.dnstr + '_' + self.notificationId + '.xml.tmp'
        s = '<?xml version="1.0"?>\n'
        s += '<notification>\n' + '\t'
        s += '<ackStateChanged  systemDN="' + self.DN + '">' + '\n' + '\t' + '\t'
        s += '<eventTime>' + str(self.now) + '</eventTime>' + '\n' + '\t' + '\t'
        s += '<specificProblem>' + self.specificProblem + '</specificProblem>' + '\n' + '\t' + '\t'
        s += '<alarmId>' + self.notificationId + '</alarmId>' + '\n' + '\t' + '\t'
        s += '<ackStatus>%s</ackStatus>' % operation + '\n' + '\t'
        s += '</ackStateChanged>' + '\n'
        s += '</notification>\n'
        self.content = s
        Logger.debug(self.content)
        self.send()
        Logger.info("{} alarm success!".format(operation))
        Logger.info("alarmId: {}".format(self.consecNbr))

    def newalarm(self):
        if 'SDM' in self.DN:
            # SDM
            self.dnstr = self.DN.split('/')[0] + '%2F' + self.DN.split('/')[1]
            self.DN = self.DN[self.DN.index("SDM"):]
        elif 'FU' in self.DN:
            control_object = input("pls input the controlObject of DN:")
            self.dnstr = control_object.replace('/', '%2F')
        else:
            self.dnstr = self.DN.replace('/', '%2F')

        self.fileName = self.fm_folder + 'an_fqdn_' + self.dnstr + '_' + self.notificationId + '.xml.tmp'
        s = '<?xml version="1.0"?>\n'
        s += '<notification>\n' + '\t'
        s += '<alarmNew  systemDN="' + self.DN + '">' + '\n' + '\t' + '\t'
        s += '<eventTime>' + str(self.now) + '</eventTime>' + '\n' + '\t' + '\t'
        s += '<specificProblem>' + self.specificProblem + '</specificProblem>' + '\n' + '\t' + '\t'
        s += '<alarmText>' + self.alarmText + '</alarmText>' + '\n' + '\t' + '\t'
        s += '<perceivedSeverity>' + self.perceivedSeverity + '</perceivedSeverity>' + '\n' + '\t' + '\t'
        s += '<eventType>' + self.eventType + '</eventType>' + '\n' + '\t' + '\t'
        s += '<probableCause>81</probableCause>' + '\n' + '\t' + '\t'
        s += '<alarmId>' + self.notificationId + '</alarmId>' + '\n' + '\t' + '\t'
        s += '<additionalText1>' + self.additionalText1 + '</additionalText1>' + '\n' + '\t' + '\t'
        s += '<additionalText2>' + self.additionalText2 + '</additionalText2>' + '\n' + '\t' + '\t'
        s += '<additionalText3>' + self.additionalText3 + '</additionalText3>' + '\n' + '\t' + '\t'
        s += '<additionalText4>' + self.additionalText4 + '</additionalText4>' + '\n' + '\t' + '\t'
        s += '<additionalText5>' + self.additionalText5 + '</additionalText5>' + '\n' + '\t' + '\t'
        s += '<additionalText6>' + self.additionalText6 + '</additionalText6>' + '\n' + '\t' + '\t'
        s += '<additionalText7>' + self.additionalText7 + '</additionalText7>' + '\n' + '\t'
        s += '</alarmNew>' + '\n'
        s += '</notification>\n'
        self.content = s
        Logger.debug(self.content)
        self.send()
        maxtime = time.time() + 30
        while 1:
            if time.time() > maxtime:
                Logger.error("create alarm failed!")
                Logger.error("cause by: DN maybe error or fm_pipe be broken")
                Logger.error("ofasFile put into fm_pipe folder: {}".format(self.ofas_file_path))
                exit(1)
            alarm_id = self.get_alarm_id()
            if alarm_id:
                Logger.info("create alarm success!")
                Logger.info("alarmId: {}".format(alarm_id))
                break
            time.sleep(2)

    @property
    def now(self):
        if self.eventTime:
            return self.eventTime
        else:
            return datetime.datetime.now().strftime("%Y-%m-%dT%X")

    def get_alarm_id(self):
        sqlplus = Popen(['sqlplus', '%s/%s' % (self.sqlplus_user, self.sqlplus_passwd)], stdout=PIPE, stdin=PIPE)
        sqlplus.stdin.write("select CONSEC_NBR from fx_alarm where DN ='{}' and ALARM_NUMBER={} and NOTIFICATION_ID={};{}".format(self.DN, self.specificProblem, self.notificationId, os.linesep).encode('utf-8'))
        stdout, err = sqlplus.communicate()
        stdout, err = stdout.decode('utf-8'), err.decode('utf-8')
        pattern = re.compile(r"(^CONSEC_NBR\s+)(^-+\s+)(^[\s0-9]+)", re.M | re.S)
        for m in pattern.finditer(stdout):
            return m.group(3).strip()

    def get_alarm_info(self):
        sqlplus = Popen(['sqlplus', '%s/%s' % (self.sqlplus_user, self.sqlplus_passwd)], stdout=PIPE, stdin=PIPE)
        sqlplus.stdin.write(
            "select DN,ALARM_NUMBER,NOTIFICATION_ID  from fx_alarm where CONSEC_NBR = %s;" % self.consecNbr + os.linesep)
        stdout, err = sqlplus.communicate()
        stdout, err = stdout.decode('utf-8'), err.decode('utf-8')
        pattern = re.compile(r"(^NOTIFICATION_ID\s+)(^-+\s+)(.+)(^SQL>.*)", re.M | re.S)
        for m in pattern.finditer(stdout):
            result = m.group(3).strip()
            result_list = result.split("\n")
            return result_list[0].strip(), result_list[1].strip(), result_list[2].strip()
        Logger.error("alarm: {} is not exist".format(self.consecNbr))
        exit(1)

    def send(self):
        with open(self.fileName, 'w') as f:
            f.write(self.content)
        execute_command("chown omc:sysop {file} && chmod 775 {file}".format(file=self.fileName))
        self.ofas_file_path = self.fm_folder + 'an_fqdn_' + self.dnstr + '_' + self.notificationId + '.xml'
        execute_command("mv {} {}".format(self.fileName, self.ofas_file_path))
        Logger.debug("ofas file be generated: {}".format(self.ofas_file_path))


def args_parser():
    version = '1.1'
    opt = optparse.OptionParser(version=version)
    operation_choices = ['new', 'ack', 'unack', 'change', 'clear']
    opt.add_option("-o", action='store', help="Mandatory,support: {}".format(operation_choices), dest="operation",
                   choices=operation_choices)
    opt.add_option("-d", "--dn", action='store', help="Mandatory for new operation,example: PLMN-PLMN/RNC-1", dest="dn")
    opt.add_option("-c", "--alarmId", action='store', help="Mandatory for {} operation".format(operation_choices[1:]),
                   dest="consecNbr")
    opt.add_option("-s", "--alarmNumber", action='store', help="Optional for new operation. example: 60001", dest="specificProblem",
                   default="50000")
    opt.add_option("-n", "--notificationId", action='store', help="Optional for new operation. example: 168", dest="notificationId",
                   default=str(int(time.time())))
    opt.add_option("--perceivedSeverity", action='store',
                   help="Optional for new,change operation. support: [critical,warning,major,minor]",
                   dest="perceivedSeverity", default="critical")
    opt.add_option("--eventType", action='store',
                   help="Optional for new,change operation. support: [communication,processingError,environmental,qualityOfService,equipment]",
                   dest="eventType", default="communication")
    opt.add_option("--eventTime", action='store', help="such as 2020-08-31T08:28:41", dest="eventTime")
    opt.add_option("--alarmText", action='store', help="Optional for new,change operation", dest="alarmText",
                   default="alarm from sendalarm.py")
    opt.add_option("--additionalText1", action='store', help="Optional for new,change operation",
                   dest="additionalText1", default="this is additionalText1")
    opt.add_option("--additionalText2", action='store', help="Optional for new,change operation",
                   dest="additionalText2", default="this is additionalText2")
    opt.add_option("--additionalText3", action='store', help="Optional for new,change operation",
                   dest="additionalText3", default="this is additionalText3")
    opt.add_option("--additionalText4", action='store', help="Optional for new,change operation",
                   dest="additionalText4", default="this is additionalText4")
    opt.add_option("--additionalText5", action='store', help="Optional for new,change operation",
                   dest="additionalText5", default="this is additionalText5")
    opt.add_option("--additionalText6", action='store', help="Optional for new,change operation",
                   dest="additionalText6", default="this is additionalText6")
    opt.add_option("--additionalText7", action='store', help="Optional for new,change operation",
                   dest="additionalText7", default="this is additionalText7")
    opt.add_option("--debug", action='store_true', help="enable debug log", dest="debug")
    _options, _args = opt.parse_args()
    return _options


def check_args(_options):
    if _options.operation == "new":
        if not _options.dn:
            Logger.error("argument -d is missing")
            exit(1)
    elif _options.operation in ("ack", "unack", "change", "clear"):
        if not _options.consecNbr:
            Logger.error("argument -c is missing")
            exit(1)


if __name__ == '__main__':
    options = args_parser()
    check_args(options)
    if options.debug:
        Logger.enable_debug()
    if options.operation == "new":
        notify = Notification(options)
        notify.newalarm()
    elif options.operation in ("ack", "unack"):
        notify = Notification(options)
        notify.ackalarm()
    elif options.operation == "change":
        notify = Notification(options)
        notify.change_alarm()
    elif options.operation == "clear":
        notify = Notification(options)
        notify.clear()
