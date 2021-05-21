import subprocess
import logging
from os.path import join, dirname, abspath
import re
import time
import random
import datetime
import os
import optparse
import signal
import sys


class Logger(object):
    logger = logging.getLogger("Logger")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s: %(message)s')
    handler = logging.FileHandler(join(dirname(abspath(__file__)), 'alarm_simulator.log'))
    # handler = logging.StreamHandler()
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
        print(message)

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
    stdout = stdout.strip()
    stderr = process.stderr.read()
    stderr = stderr.strip()
    return stdout.decode('utf-8'), stderr.decode('utf-8')


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
    def __init__(self):
        super(Alarms, self).__init__()
        self.fm_pipe_root = '/var/opt/nokia/oss/global/mediation/south/fm/import/'
        self._dn_list = []

    @property
    def dn_list(self):
        if not self._dn_list:
            self._dn_list = self._extract_dns()
        return self._dn_list

    @staticmethod
    def _extract_dns():
        # only read nasda table
        sql = "select co_dn from nasda_objects"
        out = execute_sqlplus_command(sql)
        nasdas = out.split('\n')
        pattern = re.compile(r'^PLMN-[a-zA-Z0-9-]+/[a-zA-Z0-9-]+')
        nasdas = filter(lambda nasda: pattern.match(nasda), nasdas)
        dn_list = list(map(lambda nasda: pattern.match(nasda).group(), nasdas))
        if 'PLMN-PLMN/NETACT-12345678' in dn_list:
            dn_list.remove('PLMN-PLMN/NETACT-12345678')
        if not dn_list:
            Logger.error('nasda has 0 objects.')
            exit(1)
        else:
            Logger.info('extract {} mo from nasda table'.format(len(dn_list)))
            return dn_list

    def _new_alarm_texts(self, count=1, severity='critical', dn=None):
        alarms = []
        contents = list()
        contents.append('<?xml version="1.0" encoding="utf-8"?>')
        contents.append('<notification>')

        for i in range(count):
            if not dn:
                dn = random.choice(self.dn_list)
            alarm_id = '{}{}'.format(int(time.time() * 1000), i)
            content = """
            <alarmNew systemDN="{dn}">
            <eventTime>{event_time}</eventTime>
            <specificProblem>54188</specificProblem>
            <alarmText>alarm from alarm simulator</alarmText>
            <perceivedSeverity>{severity}</perceivedSeverity>
            <eventType>communication</eventType>
            <probableCause>81</probableCause>
            <alarmId>{alarm_id}</alarmId>
            <additionalText1>additionalText1</additionalText1>
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
        file_name = 'an_fqdn_{dn}_{alarm_id}.xml'.format(dn=dn.replace('/', '%2F'), alarm_id=alarm_id)
        Logger.debug('\n'.join(contents))
        Logger.debug('ofas file: {}'.format(file_name))
        return file_name, '\n'.join(contents), alarms

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
        while 1:
            if not os.path.exists(file_name):
                break
            time.sleep(0.1)

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
        consuming_start = time.time()
        self._move_to_fm_pipe(file_name)
        consuming_end = time.time()
        return consuming_end - consuming_start

    def new_alarms(self, count=1, severity='warning', dn=None):
        start_time = time.time()
        file_name, alarm_text, alarms = self._new_alarm_texts(count, severity, dn)
        fm_process_cost = self._send_alarms(file_name, alarm_text)
        end_time = time.time()
        return fm_process_cost, end_time - start_time

    def _is_burst(self):
        current_time = datetime.datetime.now()
        for _burst_time_range in self._burst_time_range_list:
            if _burst_time_range[0] < current_time < _burst_time_range[1]:
                return True
        return False

    def _is_peak(self):
        current_time = datetime.datetime.now()
        for _peak_time_range in self._peak_time_range_list:
            if _peak_time_range[0] < current_time < _peak_time_range[1]:
                return True
        return False

    @property
    def _burst_time_range_list(self):
        return [(self._get_today_timestamp(_date='16:00'), self._get_today_timestamp(_date='17:00'))]

    @property
    def _peak_time_range_list(self):
        return [(self._get_today_timestamp(_date='04:00'), self._get_today_timestamp(_date='04:05')),
                (self._get_today_timestamp(_date='12:00'), self._get_today_timestamp(_date='12:05')),
                (self._get_today_timestamp(_date='20:00'), self._get_today_timestamp(_date='20:05'))]

    @staticmethod
    def _get_today_timestamp(_date="00:00"):
        return datetime.datetime.strptime(str(datetime.datetime.now().date()) + _date, '%Y-%m-%d%H:%M')

    def get_batch_size(self, constant, burst, peak, forceburst, forcepeak):
        if forceburst:
            return burst
        elif forcepeak:
            return peak
        elif self._is_burst():
            return burst
        elif self._is_peak():
            return burst
        else:
            return constant


def batched_create_alarms(constant, burst, peak, interval, forceburst, forcepeak, dn):
    # events = warning alarm * 3
    constant /= 3
    burst /= 3
    peak /= 3
    o = Alarms()
    previous_timestamp = time.time()
    while 1:
        current_timestamp = time.time()
        cost_time = current_timestamp - previous_timestamp
        if cost_time > interval:
            alarm_count = o.get_batch_size(constant, burst, peak, forceburst, forcepeak)
            fm_process_cost, total_cost = o.new_alarms(alarm_count * interval, dn=dn)
            Logger.info("send event count: {}, fm process cost: {}s, total cost: {}, throughput: {}/s, dn: {}".format(
                alarm_count * 3 * interval, fm_process_cost, total_cost, int(alarm_count * 3 * interval / cost_time),
                dn if dn else '@auto'))
            previous_timestamp = current_timestamp
        else:
            time.sleep(0.1)


def echo(message):
    Logger.info(message)


def exit_tool(sig, frame):
    Logger.debug('Press Ctrl+C, exit.')
    exit(0)


def argsParser():
    opt = optparse.OptionParser(version=1)
    opt.add_option("--constant", action='store', help="constant count of FM events, default is 150.", type=int,
                   dest="constant", default=150)
    opt.add_option("--burst", action='store', help="burst count of FM events, default is 470. duration: 16:00~17:00",
                   type=int,
                   dest="burst", default=470)
    opt.add_option("--peak", action='store',
                   help="peak count of FM events, default is 1170. duration: 4:00~4:05, 12:00~12:05, 20:00~20:05",
                   type=int, dest="peak",
                   default=1170)
    opt.add_option("--interval", action='store', help="interval of FM events sent, default is 10.", type=int,
                   dest="interval", default=10)
    opt.add_option("--forceburst", action='store_true', help="force burst scenario", dest="forceburst", default=False)
    opt.add_option("--forcepeak", action='store_true', help="force peak scenario", dest="forcepeak", default=False)
    opt.add_option("--dn", action='store', help="specified dn", dest="dn")
    opt.add_option("--debug", action='store_true', help="debug level", dest="debug", default=False)
    options, args = opt.parse_args()
    return options


class Deamon(object):
    def __init__(self, constant, burst, peak, interval, forceburst, forcepeak, dn):
        super(Deamon, self).__init__()
        self.running = True
        self.constant = constant
        self.burst = burst
        self.peak = peak
        self.interval = interval
        self.forceburst = forceburst
        self.forcepeak = forcepeak
        self.dn = dn

    def stop(self):
        self.running = False

    def fork(self):
        try:
            pid = os.fork()
        except OSError as err:
            print('fork failed: {}'.format(err))
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
                print('fork failed: {}'.format(err))
                sys.exit(1)
            # this is Grandson process
            self.run()
            # exit Grandson process
            sys.exit(0)
        else:
            # this is parent process . nothing to do.
            pass

    def run(self):
        batched_create_alarms(self.constant, self.burst, self.peak, self.interval, self.forceburst, self.forcepeak,
                              self.dn)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, exit_tool)
    options = argsParser()
    if options.debug:
        Logger.enable_debug()
    Logger.info("*********************Simulator*****************************")
    Logger.info("specified dn is: {}".format(options.dn))
    Logger.info("constant count of event is: {}".format(options.constant))
    Logger.info("burst count of event is: {}".format(options.burst))
    Logger.info("peak count of event is: {}".format(options.peak))
    Logger.info("interval is: {}".format(options.interval))
    Logger.info("force burst is: {}".format(options.forceburst))
    Logger.info("force peak is: {}".format(options.forcepeak))
    Logger.info("debug is: {}".format(options.debug))
    if options.forceburst and options.forcepeak:
        Logger.info("Conflict with --forceburst and --forcepeak, only one can be specified")
        exit(1)
    d = Deamon(options.constant, options.burst, options.peak, options.interval, options.forceburst, options.forcepeak,
               options.dn)
    d.fork()
