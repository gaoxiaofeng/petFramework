import subprocess
import logging
import re
import time
import random
import datetime
import os
import optparse
import signal


class Logger(object):
    logger = logging.getLogger("Logger")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s: %(message)s')
    # handler = logging.FileHandler(join(dirname(abspath(__file__)), 'prepare.log'))
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
        # print(message)

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
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout = process.stdout.read()
    stdout = stdout.decode("utf-8").strip()
    stderr = process.stderr.read()
    stderr = stderr.decode("utf-8").strip()
    return stdout, stderr


def execute_sqlplus_command(sql, user='omc', password='omc'):
    command = 'echo -e "set head off;\\n {sql};" | sqlplus -s {user}/{password}'.format(sql=sql, user=user,
                                                                                        password=password)
    Logger.debug(sql)
    stdout, stderr = execute_command(command)
    if stderr:
        Logger.error(stderr)
    if stdout:
        return stdout
    return '?'


class Alarms(object):
    def __init__(self, dn):
        super(Alarms, self).__init__()
        self.fm_pipe_root = '/var/opt/nokia/oss/global/mediation/south/fm/import/'
        self._dn_list = [dn] if dn else []

    def new(self):
        pass

    @property
    def dn_list(self):
        if not self._dn_list:
            # only read nasda table
            sql = "select co_dn from nasda_objects"
            out = execute_sqlplus_command(sql)
            nasdas = out.split('\n')
            pattern = re.compile(r'^PLMN-[a-zA-Z0-9-]+/[a-zA-Z0-9-]+')
            nasdas = filter(lambda nasda: pattern.match(nasda), nasdas)
            dn_list = map(lambda nasda: pattern.match(nasda).group(), nasdas)
            dn_list = filter(lambda dn: dn not in ['PLMN-PLMN/NETACT-12345678'], dn_list)
            if not dn_list:
                Logger.error('nasda has 0 objects.')
                exit(1)
            else:
                Logger.info('extract {} objects in nasda table'.format(len(dn_list)))
            self._dn_list = dn_list
        return self._dn_list

    def _new_alarm_texts(self, count=1, severity='critical'):
        alarms = []
        contents = list()
        contents.append('<?xml version="1.0" encoding="utf-8"?>')
        contents.append('<notification>')
        alarm_id_list = []

        for i in range(count):
            dn = random.choice(self.dn_list)
            alarm_id = '{}{}'.format(int(time.time() * 1000), i)
            alarm_id_list.append(alarm_id)
            content = """
            <alarmNew systemDN="{dn}">
            <eventTime>{event_time}</eventTime>
            <specificProblem>54188</specificProblem>
            <alarmText>alarm new from prepare alarms tool</alarmText>
            <perceivedSeverity>{severity}</perceivedSeverity>
            <eventType>communication</eventType>
            <probableCause>81</probableCause>
            <alarmId>{alarm_id}</alarmId>
            <additionalText1>{severity} alarm new</additionalText1>
            <additionalText2>additionalText2</additionalText2>
            <additionalText3>additionalText3</additionalText3>
            <additionalText4>additionalText4</additionalText4>
            <additionalText5>additionalText5</additionalText5>
            <additionalText6>additionalText6</additionalText6>
            <additionalText7>additionalText7</additionalText7>
            </alarmNew>
            """.format(dn=dn,
                       event_time=datetime.datetime.now().strftime("%Y-%m-%dT%X"),
                       severity=severity,
                       alarm_id=alarm_id
                       )
            alarms.append({"id": alarm_id, "dn": dn})
            contents.append(content)
        contents.append('</notification>')
        file_name = 'an_fqdn_{dn_name}_{alarm_id}.xml'.format(dn_name=self.dn_list[0].replace('/', '%2F'),
                                                              alarm_id=alarm_id_list[-1])
        Logger.debug('\n'.join(contents))
        Logger.debug('ofas file: {}'.format(file_name))
        return file_name, '\n'.join(contents), alarms

    @staticmethod
    def _change_alarm_texts(*alarms):
        contents = list()
        contents.append('<?xml version="1.0" encoding="utf-8"?>')
        contents.append('<notification>')
        for alarm in alarms:
            content = """
            <alarmChanged  systemDN="{dn}">
            <eventTime>{event_time}</eventTime>
            <specificProblem>54188</specificProblem>
            <alarmId>{alarm_id}</alarmId>
            <perceivedSeverity>major</perceivedSeverity>
            <additionalText2>change severity to major</additionalText2>
            </alarmChanged>
            """.format(dn=alarm['dn'],
                       event_time=datetime.datetime.now().strftime("%Y-%m-%dT%X"),
                       alarm_id=alarm['id']
                       )
            contents.append(content)
        contents.append('</notification>')
        file_name = 'an_fqdn_{dn}_{alarm_id}.xml'.format(dn=alarms[0]['dn'].replace('/', '%2F'),
                                                         alarm_id=alarms[0]['id'])
        Logger.debug('\n'.join(contents))
        Logger.debug('ofas file: {}'.format(file_name))
        return file_name, '\n'.join(contents)

    @staticmethod
    def _cancel_alarm_texts(*alarms):
        contents = list()
        contents.append('<?xml version="1.0" encoding="utf-8"?>')
        contents.append('<notification>')
        for alarm in alarms:
            content = """
            <alarmCleared  systemDN="{dn}">
            <eventTime>{event_time}</eventTime>
            <specificProblem>54188</specificProblem>
            <alarmId>{alarm_id}</alarmId>
            <clearUser>omc</clearUser>
            </alarmCleared>
            """.format(dn=alarm['dn'],
                       event_time=datetime.datetime.now().strftime("%Y-%m-%dT%X"),
                       alarm_id=alarm['id']
                       )
            contents.append(content)
        contents.append('</notification>')
        file_name = 'an_fqdn_{dn}_{alarm_id}.xml'.format(dn=alarms[0]['dn'].replace('/', '%2F'),
                                                         alarm_id=alarms[0]['id'])
        Logger.debug('\n'.join(contents))
        Logger.debug('ofas file: {}'.format(file_name))
        return file_name, '\n'.join(contents)

    @staticmethod
    def _ack_alarm_texts(*alarms):
        contents = list()
        contents.append('<?xml version="1.0" encoding="utf-8"?>')
        contents.append('<notification>')
        for alarm in alarms:
            content = """
            <ackStateChanged  systemDN="{dn}">
            <eventTime>{event_time}</eventTime>
            <specificProblem>54188</specificProblem>
            <alarmId>{alarm_id}</alarmId>
            <ackUser>omc</ackUser>
            <ackStatus>acked</ackStatus>
            </ackStateChanged>
            """.format(dn=alarm['dn'],
                       event_time=datetime.datetime.now().strftime("%Y-%m-%dT%X"),
                       alarm_id=alarm['id']
                       )
            contents.append(content)
        contents.append('</notification>')
        file_name = 'an_fqdn_{dn}_{alarm_id}.xml'.format(dn=alarms[0]['dn'].replace('/', '%2F'),
                                                         alarm_id=alarms[0]['id'])
        Logger.debug('\n'.join(contents))
        Logger.debug('ofas file: {}'.format(file_name))
        return file_name, '\n'.join(contents)

    @staticmethod
    def _write_alarms_ofas(file_name, alarm_text):
        with open(file_name, 'wb') as f:
            f.write(alarm_text)

    @staticmethod
    def _change_mode(file_name):
        _, stderr = execute_command('chown omc:sysop {}'.format(file_name))
        if stderr:
            Logger.error(stderr)
            exit(1)
        _, stderr = execute_command('chmod 775 {}'.format(file_name))
        if stderr:
            Logger.error(stderr)
            exit(1)

    @staticmethod
    def _wait_file_consumed(file_name):
        Logger.info('waitting for fm_pipe consuming {}..'.format(file_name))
        while 1:
            if not os.path.exists(file_name):
                break
            time.sleep(1)
        Logger.info('fm_pipe consumed')

    def _move_to_fm_pipe(self, file_name):
        target_file = '{fm_pipe_root}{file_name}'.format(fm_pipe_root=self.fm_pipe_root, file_name=file_name)
        _, stderr = execute_command(
            'mv {file_name} {target_file}'.format(file_name=file_name, target_file=target_file))
        if stderr:
            Logger.error(stderr)
            exit(1)
        self._wait_file_consumed(target_file)

    def _send_alarms(self, file_name, alarm_text):
        self._write_alarms_ofas(file_name, alarm_text)
        self._change_mode(file_name)
        self._move_to_fm_pipe(file_name)

    def new_alarms(self, count=1, severity='warning'):
        file_name, alarm_text, alarms = self._new_alarm_texts(count, severity)
        self._send_alarms(file_name, alarm_text)
        return alarms

    def cancel_alarms(self, alarms):
        file_name, alarm_text = self._cancel_alarm_texts(*alarms)
        self._send_alarms(file_name, alarm_text)
        return alarms

    def ack_alarms(self, alarms):
        file_name, alarm_text = self._ack_alarm_texts(*alarms)
        self._send_alarms(file_name, alarm_text)
        return alarms

    def change_alarms(self, alarms):
        file_name, alarm_text = self._change_alarm_texts(*alarms)
        self._send_alarms(file_name, alarm_text)
        return alarms

    def create_cleared_alarms(self, count=1, delay_times=0):
        # ['critical', 'major', 'minor']
        alarms = self.new_alarms(count=count, severity='critical')
        self.delay(delay_times)
        self.cancel_alarms(alarms)

    def create_acked_alarms(self, count=1, delay_times=0):
        # ['critical', 'major', 'minor']
        alarms = self.new_alarms(count=count, severity='critical')
        self.delay(delay_times)
        self.ack_alarms(alarms)

    def create_change_alarms(self, count=1, delay_times=0):
        # ['critical', 'major', 'minor']
        alarms = self.new_alarms(count=count, severity='critical')
        self.delay(delay_times)
        self.change_alarms(alarms)

    def create_change_cleared_alarms(self, count=1, delay_times=0):
        # ['critical', 'major', 'minor']
        alarms = self.new_alarms(count=count, severity='critical')
        self.delay(delay_times)
        self.change_alarms(alarms)
        self.delay(delay_times)
        self.cancel_alarms(alarms)

    def create_acked_cleared_alarms(self, count=1, delay_times=0):
        # ['critical', 'major', 'minor']
        alarms = self.new_alarms(count=count, severity='critical')
        self.delay(delay_times)
        self.ack_alarms(alarms)
        self.delay(delay_times)
        self.cancel_alarms(alarms)

    def create_cleared_acked_alarms(self, count=1, delay_times=0):
        # ['critical', 'major', 'minor']
        alarms = self.new_alarms(count=count, severity='critical')
        self.delay(delay_times)
        self.cancel_alarms(alarms)
        self.delay(delay_times)
        self.ack_alarms(alarms)

    @staticmethod
    def delay(delay_time):
        if delay_time:
            Logger.info("sleep {}s".format(delay_time))
            time.sleep(delay_time)


def batched_create_alarms(alarm_type, alarm_count, dn, delay=0):
    o = Alarms(dn)
    batch_size = 100
    task_count = 0
    for i in range(alarm_count / batch_size):
        task_count += batch_size
        if alarm_type in ('new', 'all'):
            o.new_alarms(count=batch_size, severity='critical')
            echo('==========> created {} active alarms'.format(task_count))
        if alarm_type in ('acked_cleared', 'all'):
            o.create_acked_cleared_alarms(count=batch_size, delay_times=delay)
            echo('==========> created {} acked&cleared alarms'.format(task_count))
        if alarm_type in ('cleared_acked', 'all'):
            o.create_cleared_acked_alarms(count=batch_size, delay_times=delay)
            echo('==========> created {} cleared&acked alarms'.format(task_count))
        if alarm_type in ('cleared', 'all'):
            o.create_cleared_alarms(count=batch_size, delay_times=delay)
            echo('==========> created {} cleared alarms'.format(task_count))
        if alarm_type in ('acked', 'all'):
            o.create_acked_alarms(count=batch_size, delay_times=delay)
            echo('==========> created {} acked alarms'.format(task_count))
        if alarm_type in ('change', 'all'):
            o.create_change_alarms(count=batch_size, delay_times=delay)
            echo('==========> created {} change alarms'.format(task_count))
        if alarm_type in ('change_cleared', 'all'):
            o.create_change_cleared_alarms(count=batch_size, delay_times=delay)
            echo('==========> created {} change&cleared alarms'.format(task_count))

    if alarm_count % batch_size:
        remain_count = alarm_count % batch_size
        if alarm_type in ('new', 'all'):
            o.new_alarms(count=remain_count, severity='critical')
            echo('==========> created {} active alarms\n'.format(alarm_count))
        if alarm_type in ('acked_cleared', 'all'):
            o.create_acked_cleared_alarms(count=remain_count, delay_times=delay)
            echo('==========> created {} acked&cleared alarms\n'.format(alarm_count))
        if alarm_type in ('cleared_acked', 'all'):
            o.create_cleared_acked_alarms(count=remain_count, delay_times=delay)
            echo('==========> created {} cleared&acked alarms'.format(alarm_count))
        if alarm_type in ('cleared', 'all'):
            o.create_cleared_alarms(count=remain_count, delay_times=delay)
            echo('==========> created {} cleared alarms\n'.format(alarm_count))
        if alarm_type in ('acked', 'all'):
            o.create_acked_alarms(count=remain_count, delay_times=delay)
            echo('==========> created {} acked alarms\n'.format(alarm_count))
        if alarm_type in ('change', 'all'):
            o.create_change_alarms(count=remain_count, delay_times=delay)
            echo('==========> created {} change alarms'.format(alarm_count))
        if alarm_type in ('change_cleared', 'all'):
            o.create_change_cleared_alarms(count=remain_count, delay_times=delay)
            echo('==========> created {} change&cleared alarms'.format(alarm_count))


def argsParser():
    opt = optparse.OptionParser(version="1.0")
    alarm_type = ['new', 'cleared', 'acked', 'acked_cleared', 'cleared_acked', 'change', 'change_cleared', 'all']
    opt.add_option("-t", action='store', help="alarms type from {}, default is new".format(alarm_type),
                   choices=alarm_type,
                   dest="type", default='new')
    opt.add_option("-c", action='store', help="count of alarms, default is 1", type=int, dest="count", default=1)
    opt.add_option("-d", action='store', help="sleep(sec), default is 0", type=int, dest="delay", default=0)
    opt.add_option("--dn", action='store', help="optional, specified dn", dest="dn")
    opt.add_option("--debug", action='store_true', help="debug level", dest="debug")
    _options, _args = opt.parse_args()
    return _options


def echo(message):
    Logger.info(message)


def exit_tool(sig, frame):
    Logger.debug('Press Ctrl+C, exit.')
    exit(0)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, exit_tool)
    options = argsParser()
    if options.debug:
        Logger.enable_debug()
    Logger.info("alarm type is: {}".format(options.type))
    Logger.info("alarm count is: {}".format(options.count))
    Logger.info("delay: {} sec".format(options.delay))
    Logger.info("start to create alarm...")
    batched_create_alarms(options.type, options.count, options.dn, options.delay)
