from logger import Logger
from utilization import singleton
from sshlibrary import SSH
from os.path import isfile, exists
import re


@singleton
class Monitor(object):
    def __init__(self):
        self.file_rows_count = dict()
        self.file_size = dict()

    @staticmethod
    def downloadFile(host, source_file, dest_file, root_passwd):
        Logger.info('downloading: {} file'.format(source_file))
        SSH.scp(host, source_file, dest_file, password=root_passwd)
        Logger.info('downloaded file to: {}'.format(dest_file))

    def initData(self, monitor_file_path):
        if not exists(monitor_file_path) or not isfile(monitor_file_path):
            Logger.warning("Moniter file: {} is not exists, result file info will missing.".format(monitor_file_path))
            return
        with open(monitor_file_path, 'rb') as f:
            lines = f.readlines()
            lines = list(map(lambda line: line.decode('utf-8'), lines))
        for line in lines:
            info = line.split(':')[3]
            file_name = info.split(',')[0].strip()
            if file_name.endswith('gz') or file_name.endswith('zip'):
                rows_count = info.split(',')[1].strip()
                file_size = info.split(',')[2].strip()
                if rows_count.isdigit() and file_size.isdigit():
                    self.file_rows_count.update({file_name: int(rows_count)})
                    self.file_size.update({file_name: int(file_size)})
        Logger.info("found result file: {}".format(len(self.file_size)))

    def search(self, filename):
        if not filename.startswith('/var'):
            filename = '/'.join(['/var/opt/oss/restda/result', filename])
        if filename in self.file_rows_count and filename in self.file_size:
            return self.file_rows_count[filename], self.file_size[filename]
        else:
            return "?", "?"


class MonitorOperation(object):
    def __init__(self):
        super(MonitorOperation, self).__init__()

    def analyse_remote_monitor_file(self, monitor_host, root_passwd, monitor_remote_file, monitor_local_file,
                                    successful_tasks_file):
        Logger.info("analyze remote monitor file: {}".format(monitor_remote_file))
        Monitor().downloadFile(monitor_host, monitor_remote_file, monitor_local_file, root_passwd)
        return self._analyse_monitor_file(monitor_local_file, successful_tasks_file)

    def analyse_local_monitor_file(self, monitor_local_file, successful_tasks_file):
        Logger.info("analyze local monitor file: {}".format(monitor_local_file))
        return self._analyse_monitor_file(monitor_local_file, successful_tasks_file)

    def _analyse_monitor_file(self, monitor_local_file, successful_tasks_file):
        result_file_rows_count = dict()
        result_file_file_size = dict()
        Monitor().initData(monitor_local_file)
        result_file_addresses = self._extract_result_file_address(successful_tasks_file)
        length = len(result_file_addresses)
        for index, result_file_address in enumerate(result_file_addresses):
            rows_count, file_size = Monitor().search(result_file_address)
            result_file_rows_count.update({result_file_address: rows_count})
            result_file_file_size.update({result_file_address: file_size})
            if index % 1000 == 0:
                Logger.debug('analyzed {}/{} rows'.format(index + 1, length))
        return result_file_rows_count, result_file_file_size

    @staticmethod
    def _extract_result_file_address(successful_tasks_file):
        Logger.info("extract result file address from {} .".format(successful_tasks_file))
        with open(successful_tasks_file, 'rb') as f:
            lines = f.readlines()
            lines = list(map(lambda line: line.decode('utf-8'), lines))
        rows = lines[1:]
        pattern = re.compile(r'.*(plan_.*[zip|gz]).*')
        rows = filter(lambda row: pattern.match(row), rows)
        result_file_addresses = list(map(lambda row: pattern.match(row).group(1), rows))
        if result_file_addresses:
            Logger.info("found result address {} in {}".format(len(result_file_addresses), successful_tasks_file))
        else:
            Logger.error('result address is empty.')
            exit(1)

        return result_file_addresses
