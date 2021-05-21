import shutil
from utilization import singleton
from os.path import join, exists, abspath, dirname, isdir
import os
from logger import Logger
from sshlibrary import SSH
from variable import RemoteDataPath


@singleton
class CreatePlanRequests(object):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.local_data_dir = join(dirname(dirname(dirname(abspath(__file__)))), 'data')
        self.local_data_files = []

    def downloadDataFiles(self, host, root_passwd, remote_data_dir=RemoteDataPath, local_data_dir=""):
        if local_data_dir:
            self.local_data_dir = join(local_data_dir, '.requests_data')
        self._create_data_dir()
        file_paths = self._check_files(host, root_passwd, remote_data_dir)
        for file_path in file_paths:
            file_name = file_path.split('/')[-1]
            local_file_path = join(self.local_data_dir, file_name)
            self._downloadFile(host, file_path, local_file_path, root_passwd)
            self.local_data_files.append(local_file_path)

    def _create_data_dir(self):
        if not (exists(self.local_data_dir) and isdir(self.local_data_dir)):
            try:
                os.mkdir(self.local_data_dir)
            except Exception as err:
                Logger.error("create data directory failed: {}".format(self.local_data_dir))
                Logger.error(err)
                exit(1)

    @staticmethod
    def _downloadFile(host, source_file, dest_file, root_passwd):
        Logger.info('downloading request file: {}'.format(source_file))
        SSH.scp(host, source_file, dest_file, password=root_passwd)

    @staticmethod
    def _check_files(host, root_passwd, remote_data_dir):
        remote_data_dir = remote_data_dir.rstrip('/')
        command = "ls {}|grep .data$".format(remote_data_dir)
        Logger.info('checking create plan request files')
        stdout = SSH.execute_remote_command(host, command, password=root_passwd).strip()
        paths = []
        for line in stdout.split('\n'):
            file_name = line.strip()
            path = "{}/{}".format(remote_data_dir, file_name)
            paths.append(path)
        return paths

    def analysis(self, report_dir, report_file_name):
        responseTime_Maps = self._analysis_response_time()
        self._save_to_csv(responseTime_Maps, report_dir, report_file_name)
        self._clean_request_files()

    def _analysis_response_time(self):
        responseTime_Maps = dict()
        for request_file in self.local_data_files:
            Logger.info("read file: {}".format(request_file))
            with open(request_file, 'rb') as f:
                lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    try:
                        json = eval(line)
                    except Exception as err:
                        Logger.warning("analyse request response failed: {}".format(line))
                    caseId = json["caseId"]
                    ResponseTime = json["ResponseTime"]
                    if caseId not in responseTime_Maps:
                        responseTime_Maps[caseId] = [ResponseTime]
                    else:
                        responseTime_Maps[caseId].append(ResponseTime)
        return responseTime_Maps

    @staticmethod
    def _save_to_csv(responseTime_Maps, report_dir, report_file_name):
        columns = ['caseId', 'sample_count', 'average_response_time', 'maximum_response_time', 'minimum_response_time']
        content = [','.join(columns)]
        for caseId in responseTime_Maps:
            caseResponseTimes = responseTime_Maps[caseId]
            sample_count = str(len(caseResponseTimes))
            sample_sum = str(sum(caseResponseTimes))
            average_response_time = str(float(sample_sum) / float(sample_count))
            maximum_response_time = str(max(caseResponseTimes))
            minimum_response_time = str(min(caseResponseTimes))
            content.append(
                ','.join([caseId, sample_count, average_response_time, maximum_response_time, minimum_response_time]))

        result_file = join(report_dir, report_file_name)
        with open(result_file, 'wb') as f:
            f.write('\n'.join(content).encode('utf-8'))
        Logger.info('create-plan-request report file save as: {}'.format(result_file))

    def _clean_request_files(self):
        Logger.info("clean for dir: {}".format(self.local_data_dir))
        try:
            shutil.rmtree(self.local_data_dir)
        except Exception as err:
            Logger.error("remove folder: {} failed, reason: {}".format(self.local_data_dir, err))

