from variable import *
from os.path import join, exists
from utilization import remove_file
from logger import Logger
from arguments import argsParser, argsPrecheck
from environment import Environment
from zabbix import Zabbix
from request_analysis import CreatePlanRequests
from monitor_analysis import MonitorOperation
from oracle_client import OracleOperation
from pandas_operation import PandasOperation


class TasksAnalysis(object):
    def __init__(self, monitor_host, output_dir,
                 scenario_start_time, scenario_end_time, root_passwd, db_user, db_passwd, db_port):
        super(TasksAnalysis, self).__init__()
        self.environment = Environment()
        self.successful_tasks_file = join(output_dir, SuccessfulTaskFileName)
        self.failed_tasks_file = join(output_dir, FailedTaskFileName)
        self.monitor_host = monitor_host
        self.monitor_local_file = join(output_dir, LocalMonitorFileName)
        self.monitor_remote_file = RemoteMonitorFilePath
        self.output_dir = output_dir
        self.db_user = db_user
        self.db_passwd = db_passwd
        self.db_port = db_port
        self.result_file_rows_count = dict()
        self.result_file_file_size = dict()
        self.complete_sucessful_tasks_file = join(output_dir, SuccessfulCompleteTaskFileName)
        self.incomplete_successful_tasks_file = join(output_dir, SuccessfulIncompleteTaskFileName)
        self.report_file = join(self.output_dir, ReportFileName)
        self.incomplete_report_file = join(self.output_dir, IncompleteReportFileName)
        self.scenario_start_time = scenario_start_time
        self.scenario_end_time = scenario_end_time
        self.root_passwd = root_passwd

    def precheck(self):
        self.environment.precheck(self.monitor_host, self.root_passwd)
        Logger.info(
            "DB info: {}:{}@{}:{}/OSS".format(self.db_user, self.db_passwd, self.environment.db_ip, self.db_port))
        Logger.info("Scenario info: start: {} end: {}".format(self.scenario_start_time, self.scenario_end_time))
        Logger.info("Report output directory: {}".format(self.output_dir))

    def extract_tasks_from_oracle(self):
        OracleOperation().extract_tasks_from_oracle(self.environment.db_ip, self.db_user, self.db_passwd, self.db_port,
                                                    self.scenario_start_time, self.scenario_end_time,
                                                    self.failed_tasks_file, self.successful_tasks_file)

    def analyse_monitor_file(self, uselocalfile):
        if uselocalfile:
            self.result_file_rows_count, self.result_file_file_size = MonitorOperation().analyse_local_monitor_file(
                self.monitor_local_file, self.successful_tasks_file)
        else:
            self.result_file_rows_count, self.result_file_file_size = MonitorOperation().analyse_remote_monitor_file(
                self.monitor_host, self.root_passwd, self.monitor_remote_file, self.monitor_local_file,
                self.successful_tasks_file)

    def _aggregate_tasks(self):
        Logger.info("process {}".format(self.successful_tasks_file))
        filtered_file = '{}.filtered'.format(self.successful_tasks_file)
        PandasOperation().filter_for_running_cost_and_total_cost_column(self.successful_tasks_file, filtered_file)
        data = PandasOperation().read_csv(filtered_file,
                                          dtype={'total_cost': float, 'running_cost': float, 'queueing_time': float,
                                                 'result_file_rows': float, 'result_file_size': float})
        data = PandasOperation().aggregate_successful_tasks(data, self.result_file_rows_count,
                                                            self.result_file_file_size)
        PandasOperation().generate_incomplete_tasks_file_whose_result_file_info_missing(data,
                                                                                        self.incomplete_successful_tasks_file)
        PandasOperation().generate_complete_tasks_file_whose_result_file_info_exist(data,
                                                                                    self.complete_sucessful_tasks_file)
        remove_file(filtered_file)

    def analyse_tasks_generate_report(self):
        self._aggregate_tasks()
        self._generate_complete_report()
        self._generate_incomplete_report()

    def _generate_complete_report(self):
        if not exists(self.complete_sucessful_tasks_file):
            return
        report_file = self.report_file.format(self.environment.lab_name,
                                              self.scenario_start_time.replace(" ", "T").replace(":", "_"),
                                              self.scenario_end_time.replace(" ", "T").replace(":", "_"))
        PandasOperation().generate_complete_report(self.complete_sucessful_tasks_file, report_file)

    def _generate_incomplete_report(self):
        if not exists(self.incomplete_successful_tasks_file):
            return
        report_file = self.incomplete_report_file.format(self.environment.lab_name,
                                                         self.scenario_start_time.replace(" ", "T").replace(":", "_"),
                                                         self.scenario_end_time.replace(" ", "T").replace(":", "_"))
        PandasOperation().generate_incomplete_report(self.incomplete_successful_tasks_file, report_file)

    def collect_zabbix_data(self, screenid):
        Zabbix(outputdir=self.output_dir).download_screen_graphs(screenid=screenid, starttime=self.scenario_start_time,
                                                                 endtime=self.scenario_end_time)

    def clean_temporary_file(self):
        remove_file(self.complete_sucessful_tasks_file)
        remove_file(self.incomplete_successful_tasks_file)
        remove_file(self.monitor_local_file)

    def analyse_requests(self):
        r = CreatePlanRequests()
        r.downloadDataFiles(self.monitor_host, self.root_passwd, local_data_dir=self.output_dir)
        scenario_start_time = self.scenario_start_time.replace(" ", "T").replace(":", "_")
        scenario_end_time = self.scenario_end_time.replace(" ", "T").replace(":", "_")
        report_name = '{}_{}_to_{}_requests_response_time_analysis.csv'.format(self.environment.lab_name,
                                                                               scenario_start_time, scenario_end_time)
        r.analysis(self.output_dir, report_name)


def main():
    options = argsParser()
    argsPrecheck(options)
    t = TasksAnalysis(options.host, options.outputdir,
                      options.starttime, options.endtime,
                      options.rootpasswd, options.dbuser, options.dbpasswd, options.dbport)
    t.precheck()
    if options.onlyzabbix:
        t.collect_zabbix_data(options.screenid)
        return
    if options.skipexport:
        Logger.info("skip export task from oracle datebase.")
    else:
        t.extract_tasks_from_oracle()
    t.analyse_monitor_file(options.uselocalfile)
    t.analyse_tasks_generate_report()
    if options.skiprequest:
        Logger.info("skip query requests analysis.")
    else:
        t.analyse_requests()
    if options.skipzabbix:
        Logger.info("skip capture zabbix picture.")
    else:
        t.collect_zabbix_data(options.screenid)
    t.clean_temporary_file()


if __name__ == '__main__':
    main()
