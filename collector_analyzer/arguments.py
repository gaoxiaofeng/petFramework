import optparse
from os.path import join, exists, abspath, dirname, isdir
from logger import Logger
import time
import datetime


def argsParser():
    default_report_dir = join(dirname(abspath(__file__)), 'reports')
    opt = optparse.OptionParser(version=1)
    opt.add_option("--start", action='store', help="scenario start time, format: YYYY-MM-DD HH:mm:SS", dest="starttime",
                   default='2019-11-25 00:00:00')
    opt.add_option("--end", action='store', help="scenario end time, format: YYYY-MM-DD HH:mm:SS", dest="endtime",
                   default='2020-11-26 00:00:00')
    opt.add_option("--rootpasswd", action='store', help="root password in test lab, default is arthur.",
                   dest="rootpasswd", default='arthur')
    opt.add_option("--host", action='store', help="simulator_primary_host in setup/setup_config.yml", dest="host", default='10.32.192.144')
    opt.add_option("--dbuser", action='store', help="oracle user, default is omc.", dest="dbuser", default='omc')
    opt.add_option("--dbpasswd", action='store', help="oracle user, default is omc.", dest="dbpasswd", default='omc')
    opt.add_option("--dbport", action='store', help="oracle port, default is 1521.", dest="dbport", default=1521,
                   type=int)
    opt.add_option("--outputdir", action='store',
                   help="output file directory, default is {}".format(default_report_dir), dest="outputdir",
                   default=default_report_dir)
    opt.add_option("--screenid", action='store',
                   help="zabbix screen id, default is 238(vsp0038 screen)", dest="screenid",
                   default="238")
    opt.add_option("--skipzabbix", action='store_true', help="skip capture zabbix picture", dest="skipzabbix")
    opt.add_option("--skipexport", action='store_true', help="skip export task from db", dest="skipexport")
    opt.add_option("--uselocalfile", action='store_true', help="use local monitor file", dest="uselocalfile")
    opt.add_option("--skiprequest", action='store_true', help="skip request analysis", dest="skiprequest")
    opt.add_option("--onlyzabbix", action='store_true', help="only capture zabbix picture", dest="onlyzabbix")
    opt.add_option("--debug", action='store_true', help="debug mode", dest="debug")
    options, args = opt.parse_args()
    return options


def argsPrecheck(options):
    if exists(options.outputdir) and isdir(options.outputdir):
        Logger.enable_log_file(options.outputdir)
    if options.debug:
        Logger.set_debug_level()
    try:
        start_timestamp = int(
            time.mktime(datetime.datetime.strptime(options.starttime, "%Y-%m-%d %H:%M:%S").timetuple()))
        end_timestamp = int(time.mktime(datetime.datetime.strptime(options.endtime, "%Y-%m-%d %H:%M:%S").timetuple()))
    except Exception as err:
        Logger.error("parameter starttime or endtime is invalid, example: 2019-12-01 13:20:00")
    else:
        if end_timestamp < start_timestamp:
            Logger.error("parameter starttime > endtime.")
    if not (exists(options.outputdir) and isdir(options.outputdir)):
        Logger.error("output dir: {} is not exists, please created first.".format(options.outputdir))
    if not options.screenid.isdigit():
        Logger.error("paramenter screenid is not digit".format(options.outputdir))
    if Logger.has_error():
        exit(1)
