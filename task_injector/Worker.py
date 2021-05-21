import os
import queue as Queue
import sys
import time
from multiprocessing import Process
from threading import Thread
import traceback
from CaseHandler import CaseHandler
from Logger import Log, Debug
from QueueServer import QueueManager
from Variable import *


class WorkerServer(Process):
    def __init__(self, **kwargs):
        super(WorkerServer, self).__init__()
        self.running = True
        self.workerId = kwargs["workerId"]
        self.caseId = kwargs["caseId"]
        self.dataPath = kwargs["dataPath"]
        self.Expiration = kwargs["Expiration"]
        self.ThinkTime = kwargs["ThinkTime"]
        self.CaseHandler = CaseHandler()
        self.PassTask = kwargs["PassTask"]
        self.FailTask = kwargs["FailTask"]
        self.delayStarted = kwargs["delayStarted"]
        self.inputQueue = kwargs["inputQueue"]
        self.outputQueue = kwargs["outputQueue"]
        self.MaxCount = kwargs["MaxCount"]

    @property
    def input_queue(self):
        if self.manager:
            return getattr(self.manager, self.inputQueue)()
        else:
            raise Exception("input_queue is error. ")

    @property
    def output_queue(self):
        if self.manager:
            return getattr(self.manager, self.outputQueue)()
        else:
            raise Exception("output_queue is error")

    def run(self):
        input_queue = "inputQueue_{}".format(self.workerId)
        output_queue = "outputQueue_{}".format(self.workerId)
        QueueManager.register(input_queue)
        QueueManager.register(output_queue)
        server_addr = 'localhost'
        self.manager = QueueManager(address=(server_addr, 5000), authkey=b'abc')
        try:
            self.manager.connect()
        except Exception as err:
            Log().error("Worker connect Master Server refuse! error: {}".format(err))
            sys.exit(0)
        self.WorkerHeartBeat = WorkerHeartBeat(worker_id=self.workerId, output_queue=self.output_queue)
        self.WorkerHeartBeat.setDaemon(True)
        self.WorkerHeartBeat.start()
        self.WorkerTaskRunner = WorkerTaskRunner(workerId=self.workerId,
                                                 caseId=self.caseId,
                                                 delayStarted=self.delayStarted,
                                                 dataPath=self.dataPath,
                                                 ThinkTime=self.ThinkTime,
                                                 output_queue=self.output_queue,
                                                 PassTask=self.PassTask,
                                                 FailTask=self.FailTask,
                                                 MaxCount=self.MaxCount)
        self.WorkerTaskRunner.setDaemon(True)
        self.WorkerTaskRunner.start()

        while self.running:
            try:
                if time.time() > self.Expiration:
                    self.stop()
                # if not isOpen("localhost",5000):
                #     break
                self.command_process()
                if not self.WorkerTaskRunner.is_alive():
                    self.stop()

            except Exception as err:
                self.upload_exception(str(err))
                self.stop()

    def upload_status(self, status):
        send_json = [{"workerId": self.workerId, "status": status}]
        try:
            self.output_queue.put(send_json)
        except Exception as err:
            # the QueueServer already exit.
            pass

    def upload_exception(self, error):
        send_json = [{"workerId": self.workerId, "status": CRASH, "errorReason": error}]
        try:
            self.output_queue.put(send_json)
        except Exception as err:
            # the QueueServer already exit.
            pass

    def command_process(self):
        try:
            command_json = self.input_queue.get(block=False)
        except Queue.Empty:
            pass
        except Exception as err:
            raise Exception("connection between masterServer and Worker is broken. err: {}".format(err))
        else:
            for command_dict in command_json:
                if command_dict["workerId"] == self.workerId and command_dict["operation"] == DO_STOP:
                    self.upload_status(STOPED)
                    self.stop()

    def stop(self):
        self.running = False
        self.WorkerHeartBeat.stop()
        self.WorkerHeartBeat.join(timeout=3)
        self.WorkerTaskRunner.stop()
        self.WorkerTaskRunner.join(timeout=3)
        self.upload_status(STOPED)


class WorkerHeartBeat(Thread):
    def __init__(self, worker_id, output_queue):
        super(WorkerHeartBeat, self).__init__()
        self.running = True
        self.output_queue = output_queue
        self.workerId = worker_id

    def run(self):
        while self.running:
            send_json = [{"heartBeat": int(time.time()), "workerId": self.workerId, "pid": os.getpid()}]
            try:
                self.output_queue.put(send_json)
            except Exception as err:
                # Queue Server exit.
                pass
            time.sleep(2)

    def stop(self):
        self.running = False


class WorkerTaskRunner(Thread):
    def __init__(self, **kwargs):
        super(WorkerTaskRunner, self).__init__()
        self.PassTask = kwargs["PassTask"]
        self.FailTask = kwargs["FailTask"]
        self.workerId = kwargs["workerId"]
        self.output_queue = kwargs["output_queue"]
        self.caseId = kwargs["caseId"]
        self.CaseHandler = CaseHandler()
        self.running = True
        self.delayStarted = kwargs["delayStarted"]
        self.dataPath = kwargs["dataPath"]
        self.ThinkTime = kwargs["ThinkTime"]
        self.MaxCount = kwargs["MaxCount"]

    def run(self):
        time.sleep(self.delayStarted)
        self.upload_status(STARTED)
        case_object = self.CaseHandler.cases[self.caseId]
        try:
            case_object.setattr(workerId=self.workerId, dataPath=self.dataPath)
            case_object.do_pre_action()
            while self.running:
                if self.MaxCount and self.PassTask >= self.MaxCount:
                    break
                try:
                    case_object.do_action()
                    self.PassTask += 1
                    self.upload_task_status()
                except Exception as err:
                    self.FailTask += 1
                    self.upload_task_status(error="Worker do action failed: {}".format(err))
                finally:
                    time.sleep(self.ThinkTime)

            case_object.do_post_action()
        except Exception as err:
            self.upload_exception("Worker do post action failed: {}".format(err))

    def upload_status(self, status):
        send_json = [{"workerId": self.workerId, "status": status}]
        try:
            self.output_queue.put(send_json)
        except Exception as err:
            # the QueueServer already exit.
            Debug.error("Worker upload status failed: {}. {}".format(err, traceback.format_exc()))

    def upload_exception(self, error):
        send_json = [{"workerId": self.workerId, "status": CRASH, "errorReason": error}]
        try:
            self.output_queue.put(send_json)
        except Exception as err:
            # the QueueServer already exit.
            Debug.error("Worker upload exception failed: {}. {}".format(err, traceback.format_exc()))

    def upload_task_status(self, error=None):
        status = {"workerId": self.workerId, "PassTask": self.PassTask, "FailTask": self.FailTask}
        if error:
            status.update({"Exception": error})
        send_json = [status]
        try:
            self.output_queue.put(send_json)
        except Exception as err:
            # the QueueServer already exit.
            Debug.error("Worker upload task status failed: {}. {}".format(err, traceback.format_exc()))

    def stop(self):
        self.running = False
