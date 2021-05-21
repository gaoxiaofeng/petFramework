import os
import queue as Queue
import sys
import time

from Logger import Log
from QueueServer import QueueManager
from Utility import is_open
from Variable import *


class MasterClient(object):
    def __init__(self):
        super(MasterClient, self).__init__()
        self.running = True

    def connect(self):
        QueueManager.register('master_input_queue')
        QueueManager.register('master_output_queue')
        server_addr = 'localhost'
        self.manager = QueueManager(address=(server_addr, 5000), authkey=b'abc')
        self.manager.connect()

    def one_click_start(self):
        command = "start"
        self.input_queue.put(command)
        result = self._wait_until_feedback()
        return result

    def one_click_stop(self):
        command = "stop"
        self.input_queue.put(command)
        result = self._wait_until_feedback()
        return result

    def one_click_result(self):
        command = "result"
        self.input_queue.put(command)
        result = self._wait_until_feedback()
        return result

    def one_click_check(self):
        command = "check"
        self.input_queue.put(command)
        result = self._wait_until_feedback()
        return result

    def one_click_clean(self):
        command = "clean"
        self.input_queue.put(command)
        result = self._wait_until_feedback()
        return result

    def one_click_exit(self):
        command = "exit"
        self.input_queue.put(command)
        result = self._wait_until_feedback()
        return result

    def _wait_until_feedback(self):
        while 1:
            try:
                result = self.output_queue.get(block=False)
            except Queue.Empty:
                continue
            else:
                return result

    def start(self, console=True):
        startTime = time.time()
        while time.time() - startTime < 3:
            # wait for masterServer ready.
            if is_open("localhost", 5000):
                break
            time.sleep(0.1)
        if not is_open("localhost", 5000):
            return
        try:
            self.connect()
        except Exception as err:
            Log().error("Master Client connect Master Server refuse! error: {}".format(err))
            sys.exit(0)
        else:
            Log().info("Master Client attach successful.")
        if console:
            self.run()

    @property
    def input_queue(self):
        if self.manager:
            return self.manager.master_input_queue()
        else:
            raise Exception("input_queue is error. ")

    @property
    def output_queue(self):
        if self.manager:
            return self.manager.master_output_queue()
        else:
            raise Exception("output_queue is error")

    def run(self):
        Log().info("client pid<{}>".format(os.getpid()))
        Log().info("you can use command {}`help`{}.".format(PRINT_GREEN, PRINT_END))
        while self.running:
            input_command = input("{}Master:{}".format(PRINT_GREEN, PRINT_END))
            input_command = input_command.strip()
            if not input_command:
                continue
            if input_command:
                self.send_request(input_command)
                resp = self.read_response()
                if isinstance(resp, list) and "Bye" in resp:
                    self.stop()
                    return
                else:
                    if "Bye" == resp:
                        self.stop()
                        return

    def read_response(self):
        while 1:
            try:
                resp = self.output_queue.get(block=False)
            except Queue.Empty:
                continue
            except Exception as err:
                Log().error("Connection was broken , try to auto recovery. error: {}".format(err))
                self.connect()
            else:
                Log().info(resp)
                return resp

    def send_request(self, request):
        self.input_queue.put(request)

    def stop(self):
        self.running = False
