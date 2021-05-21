import os

from Utility import mkdir
from Variable import *


class _ResultFileHandler(object):
    def __init__(self):
        super(_ResultFileHandler, self).__init__()

    @staticmethod
    def save(file_path, data):
        folder = os.path.dirname(file_path)
        mkdir(folder)
        with open(file_path, "wb") as f:
            if isinstance(data, list):
                f.write("\n".join(data).encode('utf-8'))
            else:
                f.write("{}\n".format(data).encode('utf-8'))


class Analysis(_ResultFileHandler):
    def __init__(self):
        super(Analysis, self).__init__()
        self.ResponseTimes = []

    def parse(self, file_path, maximum_response_time=True, minimum_response_time=True, average_response_time=True,
              median_response_time=True):
        if os.path.exists(file_path) and os.path.isfile(file_path):
            pass
        else:
            return {}
        result = {}
        with open(file_path, "rb") as f:
            lines = f.readlines()
        if not lines:
            # empty file
            return {}
        for line in lines:
            row = eval(line)
            status = row["status"]
            if status == PASS:
                self.ResponseTimes.append(row["ResponseTime"])
        total_rows_count = len(lines)
        first_row = eval(lines[0])
        last_row = eval(lines[-1])
        start_time = first_row["createTime"]
        end_time = last_row["createTime"]
        duration = end_time - start_time
        if not duration:
            # Duration is 0
            duration = 1
        throughput = len(self.ResponseTimes)
        speed = float(throughput) / float(duration)
        failure_count = total_rows_count - throughput
        failure_ratio = (1 - float(throughput) / float(total_rows_count)) * 100
        result.update({"Throughput": throughput,
                       "Duration": duration,
                       "Speed": speed,
                       "FailureCount": failure_count,
                       "FailureRatio": "{}%%".format(failure_ratio)})

        if self.ResponseTimes:

            response_time_exceeded_3s_count = 0
            response_time_exceeded_10s_count = 0
            response_time_exceeded_30s_count = 0
            for response_time in self.ResponseTimes:
                if response_time >= 3:
                    response_time_exceeded_3s_count += 1
                if response_time >= 10:
                    response_time_exceeded_10s_count += 1
                if response_time >= 30:
                    response_time_exceeded_30s_count += 1
            result.update({"ResponseTime_Exceeded_3s_Count": response_time_exceeded_3s_count,
                           "ResponseTime_Exceeded_10s_Count": response_time_exceeded_10s_count,
                           "ResponseTime_Exceeded_30s_Count": response_time_exceeded_30s_count,
                           "ResponseTime_Exceeded_3s_Ratio": "{} %%".format(
                               response_time_exceeded_3s_count / throughput * 100),
                           "ResponseTime_Exceeded_10s_Ratio": "{} %%".format(
                               response_time_exceeded_10s_count / throughput * 100),
                           "ResponseTime_Exceeded_30s_Ratio": "{} %%".format(
                               response_time_exceeded_30s_count / throughput * 100),
                           })

        if self.ResponseTimes and maximum_response_time:
            maximum_response_time = max(self.ResponseTimes)
            result.update({"MaximumResponseTime": maximum_response_time})
        if self.ResponseTimes and minimum_response_time:
            minimum_response_time = min(self.ResponseTimes)
            result.update({"MinimumResponseTime": minimum_response_time})
        if self.ResponseTimes and average_response_time:
            average_response_time = sum(self.ResponseTimes) / len(self.ResponseTimes)
            result.update({"AverageResponseTime": average_response_time})
        if self.ResponseTimes and median_response_time:
            self.ResponseTimes.sort()
            median_response_time = self.ResponseTimes[int(len(self.ResponseTimes) / 2)]
            result.update({"MedianResponseTime": median_response_time})
        return result


class ResultParser(_ResultFileHandler):
    def __init__(self):
        super(ResultParser, self).__init__()

    @staticmethod
    def show(file_path):
        outputs = []
        with open(file_path, "rb") as f:
            lines = f.readlines()
        if lines:
            for line in lines:
                result = eval(line)

                case_id = result["caseId"]
                average_response_time = "{} sec".format(
                    result["AverageResponseTime"] if "AverageResponseTime" in result else "NA")
                median_response_time = "{} sec".format(
                    result["MedianResponseTime"] if "MedianResponseTime" in result else "NA")
                maximum_response_time = "{} sec".format(
                    result["MaximumResponseTime"] if "MaximumResponseTime" in result else "NA")
                minimum_response_time = "{} sec".format(
                    result["MinimumResponseTime"] if "MinimumResponseTime" in result else "NA")
                # ResponseTime_Exceeded_3s_Count = result["ResponseTime_Exceeded_3s_Count"] if result.has_key("ResponseTime_Exceeded_3s_Count") else "NA"
                response_time_exceeded_3s_ratio = result[
                    "ResponseTime_Exceeded_3s_Ratio"] if "ResponseTime_Exceeded_3s_Ratio" in result else "NA"
                # ResponseTime_Exceeded_10s_Count = result["ResponseTime_Exceeded_10s_Count"] if result.has_key("ResponseTime_Exceeded_10s_Count") else "NA"
                response_time_exceeded_10s_ratio = result[
                    "ResponseTime_Exceeded_10s_Ratio"] if "ResponseTime_Exceeded_10s_Ratio" in result else "NA"
                # ResponseTime_Exceeded_30s_Count = result["ResponseTime_Exceeded_30s_Count"] if result.has_key("ResponseTime_Exceeded_30s_Count") else "NA"
                response_time_exceeded_30s_ratio = result[
                    "ResponseTime_Exceeded_30s_Ratio"] if "ResponseTime_Exceeded_30s_Ratio" in result else "NA"
                failure_count = result["FailureCount"]
                failure_ratio = result["FailureRatio"]
                throughput = result["Throughput"]
                speed = result["Speed"]
                duration = result["Duration"]
                outputs.append("*" * 20)
                outputs.append("caseId : {}{}{}".format(PRINT_GREEN, case_id, PRINT_END))
                outputs.append("Duration : {} sec".format(duration))
                outputs.append("Throughput : {}{}{}".format(PRINT_GREEN, throughput, PRINT_END))
                outputs.append("Speed : {} /s".format(speed))
                outputs.append("Failure Count : {}{}{}".format(PRINT_RED, failure_count, PRINT_END))
                outputs.append("Failure Ratio : {}{}{}".format(PRINT_RED, failure_ratio, PRINT_END))
                outputs.append("Response Time : [{} ~ {}]".format(minimum_response_time, maximum_response_time))
                outputs.append("Average Response Time : {}".format(average_response_time))
                outputs.append("Median Response Time : {}".format(median_response_time))
                outputs.append(
                    "Response Time > 3 sec : {}{}{}".format(PRINT_RED, response_time_exceeded_3s_ratio, PRINT_END))
                outputs.append(
                    "Response Time > 10 sec : {}{}{}".format(PRINT_RED, response_time_exceeded_10s_ratio, PRINT_END))
                outputs.append(
                    "Response Time > 30 sec : {}{}{}".format(PRINT_RED, response_time_exceeded_30s_ratio, PRINT_END))
        return outputs
