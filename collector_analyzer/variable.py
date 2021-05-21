SuccessfulTaskFileName = "successful_tasks.csv"
SuccessfulCompleteTaskFileName = "successful_complete_tasks.csv"
SuccessfulIncompleteTaskFileName = "successful_incomplete_tasks.csv"
FailedTaskFileName = "failed_tasks.csv"
LocalMonitorFileName = "monitor_data.txt"
RemoteMonitorFilePath = "/home/restda/monitor/monitor_result_file/Monitor.log"
RemoteDataPath = "/root/task_injector/data"
ReportFileName = "{}_{}_to_{}_report.xlsx"
IncompleteReportFileName = "{}_{}_to_{}_report[incomplete].xlsx"
ColumnList = ['task_id', 'template_id', 'status', 'template_arguments', 'running_cost', 'total_cost', 'failed_reason',
              'result_file_address', 'start_time', 'stop_time']
MandatoryColumnSet = {'task_id', 'template_id', 'template_arguments', 'result_file_address', 'total_cost',
                      'running_cost'}
ExportSucessfulTaskSqlFileName = "export_successful_tasks.sql"
