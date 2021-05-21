import os
import queue as Queue
import traceback

from Logger import Log
from QueueServer import QueueServer
from ResultHandler import ResultParser
from ScenarioHandler import ScenarioHandler
from Utility import Deamon
from Utility import singleton
from Variable import *
from WorkerHandler import WorkerHandler, WorkerProcess, WorkerMonitor


@singleton
class MasterServer(Deamon):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.WorkerHandler = None
        self.WorkerProcess = None
        self.QueueServer = QueueServer()
        self.ScenarioHandler = ScenarioHandler()
        self.scenario = None

    def set_scenario(self, scenario):
        self.scenario = scenario

    def start(self):
        self.fork()

    @property
    def input_queue(self):
        if self.QueueServer.status():
            return self.QueueServer.get_queue("master_input_queue")
        else:
            raise Exception("get master_input_queue failed , because of queue server is not started.")

    @property
    def output_queue(self):
        if self.QueueServer.status():
            return self.QueueServer.get_queue("master_output_queue")
        else:
            raise Exception("get master_output_queue failed , because of queue server is not started.")

    def get_queue(self, queue_name):
        if self.QueueServer.status():
            return self.QueueServer.get_queue(queue_name)
        else:
            raise Exception("get queue failed , because of queue server is not started.")

    def run(self):
        Log().info("master pid<{}>".format(os.getpid()))
        try:
            self.ScenarioHandler.scenario_init()
            max_cases_number = self.ScenarioHandler.max_cases_count()

            self.QueueServer.auto_register(max_cases_number)
            self.QueueServer.start()

            self.WorkerHandler = WorkerHandler()
            self.WorkerHandler.init_workers(scenario=self.scenario)

            self.WorkerProcess = WorkerProcess()
            self.WorkerProcess.setDaemon(True)
            self.WorkerProcess.start()

            self.WorkerMonitor = WorkerMonitor()
            self.WorkerMonitor.setDaemon(True)
            self.WorkerMonitor.start()
        except Exception as err:
            Log().error(PRINT_RED + str(err) + PRINT_END)
            traceback.print_exc(err)
            return

        while self.running:
            self.command_process()
            if not self.WorkerProcess.is_alive() and self.running:
                Log().error("worker process thread exit.")
            if not self.WorkerMonitor.is_alive() and self.running:
                Log().error("worker monitor thread exit.")

    def command_process(self):
        if not self.QueueServer.status():
            # queue server is not running
            return
        try:
            outputs = []
            # reduce cpu usage ratio
            command = self.input_queue.get(timeout=0.1)
            # command = self.input_queue.get(block=False)
            command = command.strip()
            if command == "help":
                output = [
                    "{}scenario{} list scenarios;".format(PRINT_GREEN, PRINT_END),
                    "{}switch <scenario>{} switch to specific scenarios;".format(PRINT_GREEN, PRINT_END),
                    "{}clean{} clean environment;".format(PRINT_GREEN, PRINT_END),
                    "{}start <workerId>{} start specific worker;".format(PRINT_GREEN, PRINT_END),
                    "{}start{} start all workers;".format(PRINT_GREEN, PRINT_END),
                    "{}stop{} stop all workers;".format(PRINT_GREEN, PRINT_END),
                    "{}stop <workerId>{} stop specific workers;".format(PRINT_GREEN, PRINT_END),
                    "{}check{} check all workers;".format(PRINT_GREEN, PRINT_END),
                    "{}check <workerId>{} check specific worker;".format(PRINT_GREEN, PRINT_END),
                    "{}status{} check all workers status;".format(PRINT_GREEN, PRINT_END),
                    "{}show <result file>{} show this result file".format(PRINT_GREEN, PRINT_END),
                    "{}result{} analysis result;".format(PRINT_GREEN, PRINT_END),
                    "{}quit{} close current console;".format(PRINT_GREEN, PRINT_END),
                    "{}exit{} close current console , and close all workers;".format(PRINT_GREEN, PRINT_END),
                ]
                self.output_queue.put(output)
            elif command == "scenario":
                for scenarioId in self.ScenarioHandler.scenarios:
                    scenario = self.ScenarioHandler.scenarios[scenarioId]
                    worker_cases = scenario.WorkerCases
                    enable = scenario.enable
                    if enable:
                        enable = PRINT_GREEN + "enable" + PRINT_END
                    else:
                        enable = PRINT_RED + "disable" + PRINT_END
                    check_result = "{} [{}]  Cases List: {} ".format(scenarioId, enable, worker_cases)
                    outputs.append(check_result)
                self.output_queue.put(outputs)
            elif command.startswith("switch"):
                if command.strip() == "switch":
                    output = "scenario is empty"
                else:
                    scenario = command.split(" ")[-1].strip()
                    if self.WorkerHandler.is_all_tasks_stoped():
                        output = "switch to {} successful".format(scenario)
                    else:
                        output = PRINT_RED + "all tasks must be stoped. switch failed." + PRINT_RED
                self.output_queue.put(output)
            elif command.startswith("start"):
                if command == "start":
                    # start all workers
                    output = self.WorkerHandler.worker_start()
                    self.output_queue.put(output)
                else:
                    # start specific worker
                    worker_id = command.split(" ")[-1]
                    output = self.WorkerHandler.worker_start(worker_id=worker_id)
                    self.output_queue.put(output)

            elif command.startswith("stop"):
                if command == "stop":
                    # stop all workers
                    output = self.WorkerHandler.worker_stop()
                    self.output_queue.put(output)
                else:
                    # stop specific worker
                    worker_id = command.split(" ")[-1]
                    output = self.WorkerHandler.worker_stop(worker_id=worker_id)
                    self.output_queue.put(output)
            elif command.startswith("c"):
                if command == "check" or command == "c":
                    # check all workers
                    output = self.WorkerHandler.worker_check()
                    self.output_queue.put(output)
                elif command.split(" ")[0] == "check" or command.split(" ")[0] == "c":
                    # check specific worker
                    worker_id = command.split(" ")[-1]
                    output = self.WorkerHandler.worker_check(worker_id=worker_id)
                    self.output_queue.put(output)
                elif command == "clean":
                    output = self.WorkerHandler.worker_clean()
                    self.output_queue.put(output)
                else:
                    output = "{} is unkown".format(PRINT_YELLOW + command + PRINT_END)
                    self.output_queue.put(output)
            elif command == "status":
                output = self.WorkerHandler.worker_status()
                self.output_queue.put(output)

            elif command == "result":
                output = self.WorkerHandler.analysis_result()
                self.output_queue.put(output)
            elif command.startswith("show"):
                if command.strip() == "show":
                    output = PRINT_RED + "result file is mandatory" + PRINT_GREEN
                else:
                    result_file = command.split(" ")[-1].strip()
                    if os.path.exists(result_file) and os.path.isfile(result_file):
                        output = ResultParser().show(result_file)
                    else:
                        not_exist = PRINT_RED + "result file {} is not exist".format(result_file + PRINT_GREEN)
                        not_file = PRINT_RED + "result file {} is not file".format(result_file + PRINT_GREEN)
                        output = not_exist if not os.path.exists(result_file) else not_file
                self.output_queue.put(output)

            elif command == "quit" or command == "q":
                output = "Bye"
                self.output_queue.put(output)
            elif command == "exit":
                output = self.WorkerHandler.stop()
                outputs.append(output)
                outputs.append("Bye")
                self.output_queue.put(outputs)
                # wait for queue be consumed by masterClient
                while True:
                    if self.output_queue.empty():
                        break
                self.stop()
            else:
                output = "{}{}{} is unkown".format(PRINT_YELLOW, command, PRINT_END)
                self.output_queue.put(output)
        except Queue.Empty:
            pass

    def stop(self):
        self.running = False
        self.WorkerMonitor.stop()
        self.WorkerMonitor.join(timeout=3)

        self.WorkerProcess.stop()
        self.WorkerProcess.join(timeout=3)

        self.QueueServer.stop()
