import json
import queue as Queue
import time
import uuid
from threading import Thread

from CaseHandler import CaseHandler
from Logger import Log, Debug
from QueueServer import QueueServer
from ResultHandler import Analysis
from ScenarioHandler import ScenarioHandler
from Utility import Cache, singleton, clean_folder
from Variable import *
from Worker import WorkerServer


@singleton
class WorkerHandler(object):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.worker_kernel = []
        self.worker_instance = {}
        self.QueueServer = QueueServer()
        self.ScenarioHandler = ScenarioHandler()
        self.CaseHandler = CaseHandler()

    @property
    def worker_cache(self):
        return self.worker_kernel

    @worker_cache.setter
    def worker_cache(self, worker_cache):
        self.worker_kernel = worker_cache

    def init_workers(self, **kwargs):
        self.CaseHandler.case_init()
        self.ScenarioHandler.scenario_init()
        scenario_id = kwargs["scenario"]
        if scenario_id:
            if scenario_id in self.ScenarioHandler.scenarios:
                # specific scenario is exit
                scenario = self.ScenarioHandler.scenarios[scenario_id]
                scenario.enable = True
            else:
                raise Exception("specified scenario {} is not exist.".format(scenario_id))
        else:
            # not specific scenario
            scenario_id = self.ScenarioHandler.default_scenario_id
            scenario = self.ScenarioHandler.scenarios[scenario_id]
            scenario.enable = True

        content = Cache().load()
        if content is None:
            # cache file is not exist
            for CaseId in scenario.WorkerCases:
                if CaseId not in self.CaseHandler.cases:
                    raise Exception("Specified Case {} is not exist.".format(CaseId))
                case = self.CaseHandler.cases[CaseId]
                if scenario.ForceThinkTime:
                    think_time = scenario.ForceThinkTime
                elif case.ThinkTime:
                    think_time = case.ThinkTime
                elif scenario.DefaultThinkTime:
                    think_time = scenario.DefaultThinkTime
                else:
                    think_time = 60
                worker_id = str(uuid.uuid4())
                data_folder = join(dirname(abspath(__file__)), "data")
                data_path = join(data_folder, "{}_{}.data".format(worker_id, CaseId))
                input_queue_name, output_queue_name = self.QueueServer.apply_queue()

                worker_kernel = {"workerId": worker_id,
                                 "status": NOT_START,
                                 "Duration": scenario.Duration,
                                 "heartBeat": None,
                                 "LastOperation": None,
                                 "inputQueue": input_queue_name,
                                 "outputQueue": output_queue_name,
                                 "cache": [],
                                 "caseId": CaseId,
                                 "PassTask": 0,
                                 "FailTask": 0,
                                 "errorReason": "",
                                 "pid": None,
                                 "dataPath": data_path,
                                 "Expiration": None,
                                 "ThinkTime": think_time,
                                 "Exception": "",
                                 "MaxCount": case.MaxCount,
                                 }
                self.worker_kernel.append(worker_kernel)
            Cache().save(self.worker_kernel)
            Log().info("creating {} workers successful".format(len(scenario.WorkerCases)))
        else:
            # cache file is exist
            Log().info("loading {} workers successful".format(len(scenario.WorkerCases)))
            self.worker_kernel = content
            for worker_kernel in self.worker_kernel:
                worker_id = worker_kernel["workerId"]
                input_queue_name, output_queue_name = self.QueueServer.apply_queue()
                self.update_worker_kernel(worker_id, {"inputQueue": input_queue_name, "outputQueue": output_queue_name})
            Cache().save(self.worker_kernel)

    def get_queue(self, queue_name):
        if self.QueueServer.status():
            return self.QueueServer.get_queue(queue_name)
        else:
            raise Exception("get queue failed , because of queue server is not started.")

    def update_worker_kernel(self, worker_id, _json):
        for worker_kernel in self.worker_kernel:
            if worker_kernel["workerId"] == worker_id:
                worker_kernel.update(_json)

    def clean_queue(self, queue_name):
        aqueue = self.get_queue(queue_name)
        while True:
            try:
                aqueue.get(block=False)
            except Queue.Empty:
                break
            except Exception as err:
                # the QueueServer already exit.
                Log().info("Clean Queue error: {}".format(err))
                break
            else:
                pass

    def worker_start(self, worker_id=None):
        delay_started = 0
        if worker_id is None:
            # start all workers
            output = []
            for w_kernel in self.worker_kernel:
                # set Expiration
                w_kernel["Expiration"] = int(time.time()) + w_kernel["Duration"]
                if w_kernel["status"] in [NOT_START, STOPED, OFFLINE, CRASH]:
                    self.clean_queue(w_kernel["inputQueue"])
                    self.clean_queue(w_kernel["outputQueue"])
                    worker = WorkerServer(workerId=w_kernel["workerId"],
                                          caseId=w_kernel["caseId"],
                                          delayStarted=delay_started,
                                          dataPath=w_kernel["dataPath"],
                                          Expiration=w_kernel["Expiration"],
                                          ThinkTime=w_kernel["ThinkTime"],
                                          inputQueue=w_kernel["inputQueue"],
                                          outputQueue=w_kernel["outputQueue"],
                                          PassTask=w_kernel["PassTask"],
                                          FailTask=w_kernel["FailTask"],
                                          MaxCount=w_kernel["MaxCount"])
                    worker.start()
                    # save worker instance
                    self.worker_instance.update({w_kernel["workerId"]: worker})
                    delay_started += 2
                    w_kernel.update({"status": STARTING, "LastOperation": int(time.time())})
                    output.append("{}worker [{}] starting...{}".format(PRINT_GREEN, w_kernel["workerId"], PRINT_END))
                else:
                    output.append("{}worker [{}] already started.{}".format(PRINT_RED, w_kernel["workerId"], PRINT_END))
            # save worker info into cache file
            self.save()
            return output
        else:
            # start specific worker
            output = []
            for w_kernel in self.worker_kernel:
                # set Expiration
                w_kernel["Expiration"] = int(time.time()) + w_kernel["Duration"]
                if w_kernel["workerId"].startswith(worker_id) and w_kernel["status"] in [NOT_START, STOPED, OFFLINE,
                                                                                         CRASH]:
                    # Log().info("start worker to do %s" % worker_kernel)
                    self.clean_queue(w_kernel["inputQueue"])
                    self.clean_queue(w_kernel["outputQueue"])
                    worker = WorkerServer(workerId=w_kernel["workerId"],
                                          caseId=w_kernel["caseId"],
                                          delayStarted=delay_started,
                                          dataPath=w_kernel["dataPath"],
                                          Expiration=w_kernel["Expiration"],
                                          ThinkTime=w_kernel["ThinkTime"],
                                          inputQueue=w_kernel["inputQueue"],
                                          outputQueue=w_kernel["outputQueue"],
                                          PassTask=w_kernel["PassTask"],
                                          FailTask=w_kernel["FailTask"],
                                          MaxCount=w_kernel["MaxCount"])
                    worker.start()
                    # save worker instance
                    self.worker_instance.update({w_kernel["workerId"]: worker})
                    w_kernel.update({"status": STARTING, "LastOperation": int(time.time())})
                    output.append("worker [{}] starting".format(w_kernel["workerId"]))
                    # save worker info into cache file
                    self.save()
                    return output
            # specific workerId is not exist
            return "{}worker [{}] is not exist.{}".format(PRINT_RED, worker_id, PRINT_END)

    def worker_stop(self, worker_id=None):
        if worker_id is None:
            # stop all workers
            output = []
            for w_kernel in self.worker_kernel:
                worker_id = w_kernel["workerId"]
                status = w_kernel["status"]
                if status in [STARTING, STOPPING, STARTED]:
                    input_queue = self.get_queue(w_kernel["inputQueue"])
                    w_kernel.update({"status": STOPPING, "LastOperation": int(time.time())})
                    send_json = [{"workerId": worker_id, "operation": DO_STOP}]
                    input_queue.put(send_json)
                    output.append("worker [{}] stopping...".format(worker_id))
                else:
                    output.append("worker [{}] already stopped.".format(worker_id))
            self.save()
            return output
        else:
            # stop specific worker
            output = []
            for w_kernel in self.worker_kernel:
                if w_kernel["workerId"].startswith(worker_id):
                    input_queue = self.get_queue(w_kernel["inputQueue"])
                    w_kernel.update({"status": STOPPING, "LastOperation": int(time.time())})
                    send_json = [{"workerId": w_kernel["workerId"], "operation": DO_STOP}]
                    output.append("worker [{}] stopping...".format(w_kernel["workerId"]))
                    input_queue.put(send_json)
                    self.save()
                    return output
            # specific workerId is not exist
            return "{}error: worker [{}] is not exist{}".format(PRINT_RED, w_kernel["workerId"], PRINT_END)

    def worker_clean(self):
        data_foler = join(dirname(abspath(__file__)), "data")
        clean_folder(data_foler)
        for worker_kernel in self.worker_kernel:
            worker_kernel.update({"PassTask": 0, "FailTask": 0, "Exception": ""})
        return "clean successful"

    def analysis_result(self):
        outputs = []
        results = []
        for worker_kernel in self.worker_kernel:
            status = worker_kernel["status"]
            if status in [STARTING, STARTED, STOPPING]:
                return PRINT_RED + "Analysis result failed , because of all workers must be stoped." + PRINT_END
        for worker_kernel in self.worker_kernel:
            data_path = worker_kernel["dataPath"]
            case_id = worker_kernel["caseId"]
            analysis = Analysis()
            result = analysis.parse(file_path=data_path)
            if result:
                result.update({"caseId": case_id})
                results.append(result)

        report_path = join(REPORT_DIR, "{}.report".format(self.ScenarioHandler.current_scenario_id))
        Analysis().save(report_path, results)

        outputs.append("Analysis successful.")
        outputs.append("Save Report file as {}".format(report_path))
        outputs.append("You can show report as below command:")
        outputs.append("{}show {}{}".format(PRINT_GREEN, report_path, PRINT_END))

        return outputs

    def workers_join(self):
        output = []
        # maxnum waiting time is 3 * Worker Count s
        start_time = time.time()
        timeout = 3 * len(self.worker_kernel)
        # wait for STOPED status be updated
        while time.time() - start_time < timeout:
            status = [w_kernel["status"] in [NOT_START, STOPED, CRASH, OFFLINE] for w_kernel in self.worker_kernel]
            if all(status):
                # all worker status is stoped.
                output.append("Close All Workers successful , cost {} s".format(round(time.time() - start_time, 3)))
                for w_kernel in self.worker_kernel:
                    output.append("workerId : {} , status : {}".format(w_kernel["workerId"], w_kernel["status"]))
                return output

        output.append("Close All Workers Timeout {} s".format(timeout))
        for w_kernel in self.worker_kernel:
            output.append("workerId : {} , status : {}".format(w_kernel["workerId"], w_kernel["status"]))
        return output

    def worker_check(self, worker_id=None):

        if worker_id:
            # check specific worker
            for w_kernel in self.worker_kernel:
                if w_kernel["workerId"].startswith(worker_id):
                    return "\n{}".format(json.dumps(w_kernel, indent=4))
            # workerId is not exist
            return "{}error: worker [{}] is not exist{}".format(PRINT_RED, worker_id, PRINT_END)
        else:
            # check all workers
            output = []
            for w_kernel in self.worker_kernel:
                worker_id = w_kernel["workerId"]
                status = w_kernel["status"]
                if status == STARTED:
                    status = PRINT_GREEN + status + PRINT_END
                elif status in [STARTING, STOPPING]:
                    status = PRINT_YELLOW + status + PRINT_END
                elif status in [OFFLINE, CRASH]:
                    status = PRINT_RED + status + PRINT_END
                else:
                    pass
                case_id = w_kernel["caseId"]
                pass_task = w_kernel["PassTask"]
                pass_task = PRINT_GREEN + str(pass_task) + PRINT_END
                fail_task = w_kernel["FailTask"]
                fail_task = PRINT_RED + str(fail_task) + PRINT_END
                exceptions = w_kernel["Exception"]
                if exceptions:
                    check_result = "{} [{}] PassTask: {}, FailTask: {}, caseId: {}, Exception: {}".format(worker_id,
                                                                                                          status,
                                                                                                          pass_task,
                                                                                                          fail_task,
                                                                                                          case_id,
                                                                                                          exceptions)
                else:
                    check_result = "{} [{}] PassTask: {}, FailTask: {}, caseId: {}".format(worker_id, status, pass_task,
                                                                                           fail_task, case_id)
                output.append(check_result)

            return output

    def worker_status(self):
        # check all workers
        output = []
        for worker_kernel in self.worker_kernel:
            output.append(worker_kernel)
        return output

    def is_all_tasks_stoped(self):
        for worker_kernel in self.worker_kernel:
            status = worker_kernel["status"]
            if status in [STARTED, STARTING, STOPPING]:
                return False
        return True

    def save(self):
        Cache().save(self.worker_kernel)

    def stop(self):
        for worker_kernel in self.worker_kernel:
            worker_id = worker_kernel["workerId"]
            status = worker_kernel["status"]
            if status == STARTED:
                self.worker_stop(worker_id=worker_id)
        output = self.workers_join()
        self.save()
        return output


class WorkerProcess(Thread):
    def __init__(self):
        super(WorkerProcess, self).__init__()
        self.QueueServer = QueueServer()
        self.WorkerHandler = WorkerHandler()
        self.running = True

    def run(self):
        while self.running:
            # sleep for reduce cpu usage ratio
            time.sleep(0.1)
            if not self.QueueServer.status():
                # QueueServer is not running
                continue
            for workerCache in self.WorkerHandler.worker_cache:
                try:
                    output_queue = self.get_queue(workerCache["outputQueue"])
                except Exception as err:
                    # Queue Server is exit.
                    break
                # read all messages in Queue
                while True:
                    try:
                        worker_output_json = output_queue.get(block=False)
                        for worker_output_dict in worker_output_json:
                            worker_id = worker_output_dict["workerId"]
                            if "Exception" in worker_output_dict:
                                exception_message = worker_output_dict.pop("Exception")
                                Debug.error(exception_message)
                            self.WorkerHandler.update_worker_kernel(worker_id, worker_output_dict)
                    except Queue.Empty:
                        break
                    except Exception as err:
                        # maybe QueueServer exit or connection broken
                        break

    def stop(self):
        self.running = False

    def get_queue(self, queue_name):
        if self.QueueServer.status():
            return self.QueueServer.get_queue(queue_name)
        else:
            raise Exception("get queue failed , because of queue server is not init.")


class WorkerMonitor(Thread):
    def __init__(self):
        super(WorkerMonitor, self).__init__()
        self.WorkerHandler = WorkerHandler()
        self.running = True

    def run(self):
        while self.running:
            # sleep for reduce cpu usage ratio
            time.sleep(1)
            # check worker instance
            # for workerId in self.WorkerHandler.workerInstance:
            #     worker = self.WorkerHandler.workerInstance[workerId]
            #     if not worker.is_alive():
            #         # process is not alive , update status to STOPED
            #         self.WorkerHandler.updateWorkerKernel(workerId, {"status": STOPED})

            for workerCache in self.WorkerHandler.worker_cache:
                worker_id = workerCache["workerId"]
                heart_beat = workerCache["heartBeat"]
                status = workerCache["status"]
                last_operation = workerCache["LastOperation"]

                # check process whether alive
                if worker_id not in self.WorkerHandler.worker_instance:
                    # worker is not init
                    self.WorkerHandler.update_worker_kernel(worker_id, {"status": NOT_START})
                else:
                    # worker is init, can be check alive status
                    worker = self.WorkerHandler.worker_instance[worker_id]
                    if not worker.is_alive():
                        self.WorkerHandler.update_worker_kernel(worker, {"status": STOPED})

                if status in [STARTING, STOPPING]:
                    if time.time() - last_operation > 30:
                        # operation timeout 30s
                        status = STOPED if status == STARTING else OFFLINE
                        self.WorkerHandler.update_worker_kernel(worker_id, {"status": status})
                if heart_beat and status in [STARTED]:
                    current_time = time.time()
                    if current_time - heart_beat > 10:
                        # heartbeat timeout 10s , set status is OFFLINE
                        self.WorkerHandler.update_worker_kernel(worker_id, {"status": OFFLINE})
                if heart_beat and status in [OFFLINE]:
                    current_time = time.time()
                    if current_time - heart_beat < 10:
                        # set online
                        self.WorkerHandler.update_worker_kernel(worker_id, {"status": STARTED})

    def stop(self):
        self.running = False
