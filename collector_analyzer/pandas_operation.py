import pandas as pd
import seaborn as sns
from logger import Logger
import time
from os.path import join, dirname, abspath
from utilization import singleton

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('max_colwidth', 1000)
pd.set_option('precision', 2)


@singleton
class PandasOperation(object):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.workingSetMaps = dict()
        self._measurementMaps = dict()

    @staticmethod
    def read_csv(source_file, dtype=None):
        if dtype:
            data = pd.read_csv(source_file, low_memory=False, dtype=dtype)
        else:
            data = pd.read_csv(source_file, low_memory=False)
        return data

    def filter_for_running_cost_and_total_cost_column(self, source_file, target_file):
        data = self.read_csv(source_file)
        data = self._filter_running_cost(data)
        data = self._filter_total_cost(data)
        data.to_csv(target_file)

    def _filter_running_cost(self, data):
        return self._filter_null(data, "running_cost")

    def _filter_total_cost(self, data):
        return self._filter_null(data, "total_cost")

    @staticmethod
    def _filter_null(data, column):
        invalid_data = data[data[column].isin(["None"])]
        valid_data = data[~data[column].isin(["None"])]
        if not invalid_data.empty:
            Logger.warning("filtered rows whose {} is null".format(column))
        return valid_data

    def aggregate_successful_tasks(self, data, result_file_rows_count, result_file_file_size):
        Logger.debug('calculate period_minute')
        data['period(min)'] = data.apply(lambda x: self._calculate_period(x.template_arguments), axis=1)
        Logger.debug('calculate working_set')
        data['wSet'] = data.apply(lambda x: self._get_workingSet(x.template_arguments), axis=1)
        Logger.debug('calculate working_set_objects')
        data['dnCount'] = data.apply(lambda x: self._get_workingSet_objectsCount(x.wSet), axis=1)
        Logger.debug('calculate include_descendants')
        data['include_descendants'] = data.apply(lambda x: self._get_includedescendants(x.template_arguments), axis=1)
        Logger.debug('calculate measurement_type')
        data['measurement_type'] = data.apply(lambda x: self._get_measurement_type(x.template_arguments), axis=1)
        Logger.debug('calculate queueing_time')
        data['queueing_time'] = data.apply(lambda x: self._calculate_queueing_time(x.running_cost, x.total_cost),
                                           axis=1)
        Logger.debug('calculate result_file_rows')
        data['result_file_rows'] = data.apply(
            lambda x: self._get_result_file_rows_count(result_file_rows_count, x.result_file_address), axis=1)
        Logger.debug('calculate result_file_size')
        data['result_file_size'] = data.apply(
            lambda x: self._get_result_file_file_size(result_file_file_size, x.result_file_address), axis=1)
        data['counter_throughput'] = data.apply(
            lambda x: self._get_counter_throughput(x.template_id, x.measurement_type, x.result_file_rows), axis=1)
        return data

    @staticmethod
    def _calculate_period(template_arguments):
        template_arguments = eval(template_arguments.replace(';', ','))
        template_arguments = template_arguments[0]
        if 'STARTTIME' in template_arguments and 'ENDTIME' in template_arguments:
            # pm template
            start_timestamp = int(time.mktime(time.strptime(template_arguments['STARTTIME'], '%Y-%m-%dT%H:%M:%S')))
            end_timestamp = int(time.mktime(time.strptime(template_arguments['ENDTIME'], '%Y-%m-%dT%H:%M:%S')))
            period = (end_timestamp - start_timestamp) / 60
        elif 'DURATION' in template_arguments:
            # delta template
            period = int(template_arguments['DURATION'])
        elif 'ALARMTIMESTART' in template_arguments and 'ALARMTIMEEND' in template_arguments:
            # activate template
            start_timestamp = int(time.mktime(time.strptime(template_arguments['ALARMTIMESTART'], '%Y-%m-%dT%H:%M:%S')))
            end_timestamp = int(time.mktime(time.strptime(template_arguments['ALARMTIMEEND'], '%Y-%m-%dT%H:%M:%S')))
            period = (end_timestamp - start_timestamp) / 60
        else:
            period = '?'
        return period

    @staticmethod
    def _get_workingSet(template_arguments):
        template_arguments = eval(template_arguments.replace(';', ','))
        template_arguments = template_arguments[0]
        if 'WORKINGSETNAME' in template_arguments:
            return template_arguments['WORKINGSETNAME']
        else:
            return '?'

    @staticmethod
    def _get_includedescendants(template_arguments):
        template_arguments = eval(template_arguments.replace(';', ','))
        template_arguments = template_arguments[0]
        if 'INCLUDEDESCENDANTS' in template_arguments:
            if template_arguments['INCLUDEDESCENDANTS'].lower() == 'true':
                return 1
            else:
                return 0
        else:
            return '?'

    def _get_workingSet_objectsCount(self, workingSetName):
        if not self.workingSetMaps:
            configuration_path = join(dirname(abspath(__file__)), 'workingset_20_ran_core.conf')
            with open(configuration_path, 'rb') as f:
                self.workingSetMaps = eval(f.read())

        if workingSetName in self.workingSetMaps:
            return self.workingSetMaps[workingSetName]
        else:
            Logger.warning("workingSet: {} is unkown. please config it firstly.".format(workingSetName))
            return '?'

    @staticmethod
    def _get_measurement_type(template_arguments):
        template_arguments = eval(template_arguments.replace(';', ','))
        template_arguments = template_arguments[0]
        if 'MEASUREMENTTYPELIST' in template_arguments:
            return template_arguments['MEASUREMENTTYPELIST']
        else:
            return '?'

    @staticmethod
    def _calculate_queueing_time(running_cost, total_cost):
        return total_cost - running_cost

    @staticmethod
    def _get_result_file_rows_count(result_file_rows_count, result_file_address):
        if result_file_address in result_file_rows_count:
            return result_file_rows_count[result_file_address]
        else:
            return "?"

    @staticmethod
    def _get_result_file_file_size(result_file_file_size, result_file_address):
        if result_file_address in result_file_file_size:
            return result_file_file_size[result_file_address]
        else:
            return "?"

    def _get_counter_throughput(self, template_id, measurement_type, result_file_rows):
        if template_id == 'Predefined_performanceData_v1':
            if measurement_type in self.measurementMaps:
                return self.measurementMaps[measurement_type] * result_file_rows
            return ""
        else:
            return ""

    @staticmethod
    def generate_incomplete_tasks_file_whose_result_file_info_missing(data, invalid_successful_tasks_file):
        invalid_data = data[data['result_file_rows'].isin(['?'])]
        if not invalid_data.empty:
            invalid_data.to_csv(invalid_successful_tasks_file)
            Logger.warning('incomplete sucessful task save as {}'.format(invalid_successful_tasks_file))
        else:
            Logger.info("incomplete successful task is empty.")

    @staticmethod
    def generate_complete_tasks_file_whose_result_file_info_exist(data, valid_sucessful_tasks_file):
        valid_data = data[~data['result_file_rows'].isin(['?'])]
        valid_data = valid_data[~valid_data['result_file_size'].isin(['?'])]
        if not valid_data.empty:
            valid_data.to_csv(valid_sucessful_tasks_file)
            Logger.info('complete successful task save as {}'.format(valid_sucessful_tasks_file))
        else:
            Logger.warning("complete successful task is empty.")

    @property
    def measurementMaps(self):
        if not self._measurementMaps:
            with open("measurement_counter.conf", "rb") as f:
                content = f.read()
            self._measurementMaps = eval(content)
        return self._measurementMaps

    def generate_complete_report(self, valid_sucessful_tasks_file, report_file):
        Logger.info('starting generate {}...'.format(valid_sucessful_tasks_file))
        # data = pd.read_csv(valid_sucessful_tasks_file,
        #                    usecols=["template_id", "measurement_type", "template_arguments", "result_file_rows",
        #                             "result_file_size", "running_cost", "queueing_time", "total_cost",
        #                             "period(min)", "wSet", "dnCount",
        #                             "include_descendants", "counter_throughput"],
        #                    dtype={'total_cost': float, 'running_cost': float, 'queueing_time': float,
        #                           'result_file_rows': float,
        #                           'result_file_size': float,
        #                           'counter_throughput': float},
        #                    low_memory=False)
        data = pd.read_csv(valid_sucessful_tasks_file,
                           usecols=["template_id", "measurement_type", "template_arguments", "result_file_rows",
                                    "result_file_size", "running_cost", "queueing_time", "total_cost",
                                    "period(min)", "wSet", "dnCount", "counter_throughput"],
                           dtype={'total_cost': float, 'running_cost': float, 'queueing_time': float,
                                  'result_file_rows': float,
                                  'result_file_size': float,
                                  'counter_throughput': float},
                           low_memory=False)
        if not len(data):
            Logger.warning("file: {} is empty.".format(valid_sucessful_tasks_file))
            return
        milestone_file = join(dirname(report_file), "milestone.csv")
        data.to_csv(milestone_file)
        Logger.info("save milestone file to: {}".format(milestone_file))
        # data_groups = data.groupby(
        #     ['template_id', 'measurement_type', 'wSet', 'dnCount', 'include_descendants',
        #      'period(min)'], sort=False)
        data_groups = data.groupby(['template_id', 'measurement_type', 'wSet', 'dnCount', 'period(min)'], sort=False)
        result = data_groups.describe(percentiles=[.5])
        self._save_excel(result, report_file)
        Logger.info('report save as: {}'.format(report_file))

    def generate_incomplete_report(self, invalid_successful_tasks_file, report_file):
        Logger.info('starting generate {}...'.format(invalid_successful_tasks_file))
        # data = pd.read_csv(invalid_successful_tasks_file,
        #                    usecols=["template_id", "measurement_type", "template_arguments",
        #                             "running_cost", "queueing_time", "total_cost", "period(min)", "wSet", "dnCount",
        #                             "include_descendants"],
        #                    dtype={'total_cost': float, 'running_cost': float, 'queueing_time': float},
        #                    low_memory=False)
        data = pd.read_csv(invalid_successful_tasks_file,
                           usecols=["template_id", "measurement_type", "template_arguments",
                                    "running_cost", "queueing_time", "total_cost", "period(min)", "wSet", "dnCount"],
                           dtype={'total_cost': float, 'running_cost': float, 'queueing_time': float},
                           low_memory=False)
        if not len(data):
            Logger.warning("file: {} has not data.".format(invalid_successful_tasks_file))
            return
        # data_groups = data.groupby(
        #     ['template_id', 'measurement_type', 'wSet', 'dnCount', 'include_descendants',
        #      'period(min)'])
        data_groups = data.groupby(['template_id', 'measurement_type', 'wSet', 'dnCount', 'period(min)'])
        result = data_groups.describe(percentiles=[.5])
        self._save_excel(result, report_file)
        Logger.info('report save as: {}'.format(report_file))

    @staticmethod
    def _save_excel(df, excel_file):
        green_color_map = sns.light_palette('green', as_cmap=True)
        purple_color_map = sns.light_palette('purple', as_cmap=True)
        seagreen_color_map = sns.light_palette('seagreen', as_cmap=True)
        blue_color_map = sns.light_palette('blue', as_cmap=True)
        # yellow_color_map = sns.light_palette('yellow', as_cmap=True)
        lawngreen_color_map = sns.light_palette('lawngreen', as_cmap=True)
        darkorange_color_map = sns.light_palette('darkorange', as_cmap=True)
        styler = df.style
        if 'running_cost' in df:
            styler = styler.background_gradient(subset=['running_cost'], cmap=green_color_map)
        if 'queueing_time' in df:
            styler = styler.background_gradient(subset=['queueing_time'], cmap=lawngreen_color_map)
        if 'total_cost' in df:
            styler = styler.background_gradient(subset=['total_cost'], cmap=purple_color_map)
        if 'result_file_rows' in df:
            styler = styler.background_gradient(subset=['result_file_rows'], cmap=darkorange_color_map)
        if 'result_file_size' in df:
            styler = styler.background_gradient(subset=['result_file_size'], cmap=seagreen_color_map)
        if 'counter_throughput' in df:
            styler = styler.background_gradient(subset=['counter_throughput'], cmap=blue_color_map)
        styler.to_excel(excel_file, engine='openpyxl', float_format="%.1f", sheet_name='restda PET report',
                        encoding='utf-8')
