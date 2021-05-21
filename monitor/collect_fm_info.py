#!/usr/bin/env python
import subprocess
import optparse
from os.path import join, dirname, abspath
import logging
import datetime
import signal


def singleton(cls, *args, **kwargs):
    instances = dict()

    def _singleton():
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return _singleton


class Logger(object):
    logger = logging.getLogger("Logger")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s: %(message)s')
    handler = logging.FileHandler(join(dirname(abspath(__file__)), 'Netact_FM_info.log'))
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    @classmethod
    def info(cls, message):
        message = message.strip()
        cls.logger.info(message)
        print(message)

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
        count = stdout.replace('result', '')
        Logger.debug(count)
        return count
    return '?'


@singleton
class SqlExecutor(object):
    _select_count = "select 'result'||count(*) from fx_alarm where {conditions}"
    _query_date_starting = "select to_date(to_char(TRUNC(SYSDATE-{offset}),'yyyy-mm-dd')||'00:00:00','yyyy-mm-dd hh24:mi:ss') from SYS.DUAL"
    _query_date_ending = "select to_date(to_char(TRUNC(SYSDATE-{offset}),'yyyy-mm-dd')||'23:59:59','yyyy-mm-dd hh24:mi:ss') from SYS.DUAL"
    _query_date = "select to_date(to_char(SYSDATE-{offset},'yyyy-mm-dd hh24:mi:ss'),'yyyy-mm-dd hh24:mi:ss') from SYS.DUAL"
    DateFormat1 = "%Y-%m-%d"
    DateFormat2 = "%Y-%m-%dT%H:%M:%S"

    def __init__(self):
        super(self.__class__, self).__init__()
        self.oracle_user = 'omc'
        self.oracle_password = 'omc'

    def set_oracle_permission(self, user, password):
        self.oracle_user = user
        self.oracle_password = password

    @classmethod
    def _log_case_description(cls, case_id, alarm_type, date_start, date_end):
        info = "[Case {}] extract {} alarms from {} to {} ...".format(case_id, alarm_type, date_start, date_end)
        Logger().info(info)

    def _excute(self, conditions, identification):
        sql = self._select_count.format(conditions=conditions)
        result = execute_sqlplus_command(sql, user=self.oracle_user, password=self.oracle_password)
        Logger.debug("[Case {}] {} ".format(identification, result))
        return result

    def _get_date_starting(self, day_offset=0):
        return '{}T00:00:00'.format(
            (datetime.datetime.now() - datetime.timedelta(days=day_offset)).strftime(self.DateFormat1))

    def _get_date_ending(self, day_offset=0):
        return '{}T23:59:59'.format(
            (datetime.datetime.now() - datetime.timedelta(days=day_offset)).strftime(self.DateFormat1))

    def _get_date(self, day_offset=0):
        return (datetime.datetime.now() - datetime.timedelta(days=day_offset)).strftime(self.DateFormat2)

    def get_short_date(self, day_offset=0):
        return (datetime.datetime.now() - datetime.timedelta(days=day_offset)).strftime(self.DateFormat1)

    def get_new_alarms_count(self, date_offset=0, identification='?'):
        self._log_case_description(identification, 'new', self._get_date_starting(date_offset),
                                   self._get_date_ending(date_offset))
        _conditions = "ALARM_TIME >= ({date_starting}) and ALARM_TIME <= ({date_ending})".format(
            date_starting=self._query_date_starting.format(offset=date_offset),
            date_ending=self._query_date_ending.format(offset=date_offset))
        count = self._excute(_conditions, identification)
        return count

    def get_active_alarms_count(self, date_offset=0, identification='?'):
        self._log_case_description(identification, 'active', self._get_date_starting(date_offset),
                                   self._get_date_ending(date_offset))
        _conditions = "not (CANCEL_TIME >= ({date_starting}) and CANCEL_TIME <= ({date_ending})) and  ALARM_TIME >= ({date_starting}) and ALARM_TIME <= ({date_ending})".format(
            date_starting=self._query_date_starting.format(offset=date_offset),
            date_ending=self._query_date_ending.format(offset=date_offset))
        count = self._excute(_conditions, identification)
        return count

    def get_warning_alarms_count(self, date_offset=0, identification='?'):
        self._log_case_description(identification, 'warning', self._get_date_starting(date_offset),
                                   self._get_date_ending(date_offset))
        _conditions = "SEVERITY = 4 and ALARM_TIME >= ({date_starting}) and ALARM_TIME <= ({date_ending})".format(
            date_starting=self._query_date_starting.format(offset=date_offset),
            date_ending=self._query_date_ending.format(offset=date_offset))
        count = self._excute(_conditions, identification)
        return count

    def get_critical_alarms_count(self, date_offset=0, identification='?'):
        self._log_case_description(identification, 'critical', self._get_date_starting(date_offset),
                                   self._get_date_ending(date_offset))
        _conditions = "SEVERITY = 1 and ALARM_TIME >= ({date_starting}) and ALARM_TIME <= ({date_ending})".format(
            date_starting=self._query_date_starting.format(offset=date_offset),
            date_ending=self._query_date_ending.format(offset=date_offset))
        count = self._excute(_conditions, identification)
        return count

    def get_history_alarms_count_by_duration(self, date_offset=0, identification='?'):
        self._log_case_description(identification, 'history', self._get_date_starting(date_offset),
                                   self._get_date_ending(date_offset))
        _conditions = "TERMINATED_TIME >= ({date_starting}) and TERMINATED_TIME <= ({date_ending})".format(
            date_starting=self._query_date_starting.format(offset=date_offset),
            date_ending=self._query_date_ending.format(offset=date_offset)
        )
        count = self._excute(_conditions, identification)
        return count

    def get_clear_and_unack_alarms_count(self, date_offset=0, identification='?'):
        self._log_case_description(identification, 'clear&unack', self._get_date_starting(date_offset),
                                   self._get_date_ending(date_offset))
        _conditions = "CANCEL_TIME >= ({date_starting}) and CANCEL_TIME <= ({date_ending}) and (not (ACK_TIME <= ({date_ending})) or ACK_STATUS=1)".format(
            date_starting=self._query_date_starting.format(offset=date_offset),
            date_ending=self._query_date_ending.format(offset=date_offset)
        )
        count = self._excute(_conditions, identification)
        return count

    def get_unclear_and_ack_alarms_count(self, date_offset=0, identification='?'):
        info = "[Case {}] extract unclear&ack alarms from {} to {}...".format(identification, self._get_date_starting(
            day_offset=date_offset),
                                                                              self._get_date_ending(
                                                                                  day_offset=date_offset))
        Logger().info(info)
        _conditions = "ACK_TIME >= ({date_starting}) and ACK_TIME <= ({date_ending}) and (not (CANCEL_TIME <= ({date_ending})) or ALARM_STATUS=1)".format(
            date_starting=self._query_date_starting.format(offset=date_offset),
            date_ending=self._query_date_ending.format(offset=date_offset)
        )
        count = self._excute(_conditions, identification)
        return count

    def get_active_alarms_count_by_duration(self, date_offset=0, identification='?'):
        info = "[Case {}] extract active alarms from {} to {}...".format(identification,
                                                                         self._get_date(day_offset=date_offset),
                                                                         self._get_date(day_offset=date_offset - 1))
        Logger().info(info)
        _conditions = "ALARM_STATUS = 1 and UPDATE_TIMESTAMP >= ({date_starting}) and UPDATE_TIMESTAMP <= ({date_ending})".format(
            date_starting=self._query_date.format(offset=date_offset),
            date_ending=self._query_date.format(offset=date_offset - 1)
        )
        count = self._excute(_conditions, identification)
        return count


def parser():
    opt = optparse.OptionParser(version='1.1', usage="use --help,-h to see cookbook")
    opt.add_option("-u", action='store', dest='user', help="oracle user, default is omc", default='omc')
    opt.add_option("-p", action='store', dest='password', help="oracle password, default is omc", default='omc')
    opt.add_option("-d", action='store', dest='duration', help="alarms period, default is 7 days", default=7, type=int)
    options, args = opt.parse_args()
    return options


def collect_fm_info(duration, user, password):
    fm_summary = []
    restda_summary = []
    SqlExecutor().set_oracle_permission(user, password)
    restda_active = SqlExecutor().get_active_alarms_count_by_duration(date_offset=1, identification="1 (latest 24h)")
    restda_summary.append('[latest 24h] restda_active: {restda_active}'.format(restda_active=restda_active))

    for i in range(1, duration + 1):
        history = SqlExecutor().get_history_alarms_count_by_duration(date_offset=i,
                                                                     identification="2 ({} days before)".format(i))
        clear_unack = SqlExecutor().get_clear_and_unack_alarms_count(date_offset=i,
                                                                     identification="3 ({} days before)".format(i))
        ack_unclear = SqlExecutor().get_unclear_and_ack_alarms_count(date_offset=i,
                                                                     identification="4 ({} days before)".format(i))
        new = SqlExecutor().get_new_alarms_count(date_offset=i, identification="5 ({} days before)".format(i))
        active = SqlExecutor().get_active_alarms_count(date_offset=i, identification="6 ({} days before)".format(i))
        warning = SqlExecutor().get_warning_alarms_count(date_offset=i, identification="7 ({} days before)".format(i))
        critical = SqlExecutor().get_critical_alarms_count(date_offset=i, identification="8 ({} days before)".format(i))
        fm_summary.append(
            '[{date}] new: {new}, active: {active}, warning: {warning}, critical: {critical}, history: {history}, clear_unack: {clear_unack}, ack_unclear: {ack_unclear}'.format(
                date=SqlExecutor().get_short_date(i), new=new, active=active, warning=warning, critical=critical,
                history=history, clear_unack=clear_unack, ack_unclear=ack_unclear
            ))
    Logger.info("=" * 80)
    Logger.info("Result-Summary:")
    Logger.info("-" * 80)
    for s in restda_summary:
        Logger.info(s)
    Logger.info("-" * 80)
    for s in fm_summary:
        Logger.info(s)
    Logger.info("-" * 80)
    print("The result save as: {}".format(join(dirname(abspath(__file__)), 'Netact_FM_info.log')))


def precheck(duration):
    stdout, stderr = execute_command('whoami')
    if stdout not in ('root', 'omc'):
        Logger.warning('current user is not root or omc!')
    if duration <= 0:
        print("args: -d duration is invalid, should be 1~14")
        exit(1)


def _exit(sig, frame):
    Logger.debug('Press Ctrl+C, exit.')
    exit(0)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, _exit)
    options = parser()
    precheck(options.duration)
    collect_fm_info(options.duration, options.user, options.password)
