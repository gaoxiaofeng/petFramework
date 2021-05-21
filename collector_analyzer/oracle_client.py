from utilization import singleton
from sqlalchemy import create_engine
from variable import *
from os.path import join, dirname, abspath
from logger import Logger


@singleton
class Oracle(object):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.connection = None

    def connect(self, host, user="omc", passwd="omc", port=1521):
        db = create_engine(
            'oracle+cx_oracle://{user}:{passwd}@{host}:{port}/OSS'.format(user=user, passwd=passwd, host=host,
                                                                          port=port),
            max_identifier_length=128)
        self.connection = db.connect()

    def _execute(self, sql):
        if not self.connection:
            raise Exception("Please connect oracle firstly!")
        ret = self.connection.execute(sql.rstrip(";"))
        return ret

    def get_rows(self, sql):
        ret = self._execute(sql)
        rows = ret.fetchall()
        return rows

    def close(self):
        if self.connection:
            self.connection.close()


class OracleOperation(object):
    def __init__(self):
        super(OracleOperation, self).__init__()
        self.export_sucessful_task_sql_file = join(dirname(abspath(__file__)), ExportSucessfulTaskSqlFileName)

    def extract_tasks_from_oracle(self, db_host, db_user, db_passwd, db_port, scenario_start_time, scenario_end_time,
                                  failed_tasks_file, successful_tasks_file):
        db = Oracle()
        try:
            db.connect(db_host, user=db_user, passwd=db_passwd, port=db_port)
        except Exception as err:
            Logger.error(err)
            Logger.error(
                "failed to connect oracle db, please check lab certificate via https://logintolabra.tre.noklab.net/dana-na/auth/url_5/welcome.cgi")
            exit(1)
        else:
            self._extract_failed_tasks(db, scenario_start_time, scenario_end_time, failed_tasks_file)
            self._extract_successful_tasks(db, scenario_start_time, scenario_end_time, successful_tasks_file)
        finally:
            db.close()

    def _extract_successful_tasks(self, db, scenario_start_time, scenario_end_time, successful_tasks_file):
        Logger.info("start export successful tasks info from {} to {}".format(scenario_start_time, scenario_end_time))
        with open(self.export_sucessful_task_sql_file, "rb") as f:
            sql_expression = f.read().strip().decode('utf-8')
        rows = db.get_rows(sql_expression.format(scenario_start_time=scenario_start_time,
                                                 scenario_stop_time=scenario_end_time))
        lines = [','.join(ColumnList)]
        for row in rows:
            row = list(row)
            row[3] = row[3].replace('"', '""')
            row = list(map(lambda x: str(x) if isinstance(x, int) or isinstance(x, float) else '"{}"'.format(x), row))
            line = ",".join(row)
            lines.append(line)
        with open(successful_tasks_file, "wb") as f:
            f.write("\n".join(lines).encode('utf-8'))
        Logger.info("exported successful tasks to file: {}".format(successful_tasks_file))
        self._precheck_successful_tasks_file(successful_tasks_file)

    @staticmethod
    def _extract_failed_tasks(db, scenario_start_time, scenario_end_time, failed_tasks_file):
        Logger.info("start export failed tasks info from {} to {}".format(scenario_start_time, scenario_end_time))
        sql_file = join(dirname(abspath(__file__)), "export_failed_tasks.sql")
        with open(sql_file, "rb") as f:
            sql_expression = f.read().strip().decode('utf-8')
        rows = db.get_rows(sql_expression.format(scenario_start_time=scenario_start_time,
                                                 scenario_stop_time=scenario_end_time))
        lines = [','.join(ColumnList)]
        for row in rows:
            row = list(row)
            row[3] = row[3].replace('"', '""')
            row = list(map(lambda x: str(x) if isinstance(x, int) or isinstance(x, float) else '"{}"'.format(x), row))
            line = ",".join(row)
            lines.append(line)
        with open(failed_tasks_file, "wb") as f:
            f.write("\n".join(lines).encode('utf-8'))
        Logger.info("exported failed tasks to file: {}".format(failed_tasks_file))

    @staticmethod
    def _precheck_successful_tasks_file(successful_tasks_file):
        Logger.info("precheck {} .".format(successful_tasks_file))
        with open(successful_tasks_file, 'rb') as f:
            lines = f.readlines()
            lines = list(map(lambda line: line.decode('utf-8'), lines))
        if len(lines) < 2:
            Logger.error("{} is empty, no successful task during this testing.".format(successful_tasks_file))
            exit(1)
        columns = [column.strip('\"\'') for column in lines[0].strip().split(',')]
        missing_columns = list(filter(lambda m: m not in columns, MandatoryColumnSet))
        if missing_columns:
            Logger.error("column: {} is missing".format(missing_columns))
            exit(1)
        Logger.info("{} format is ok.".format(successful_tasks_file))

