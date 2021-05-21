import queue as Queue
from multiprocessing.managers import BaseManager

from Utility import singleton, get_random


class QueueManager(BaseManager):
    pass


@singleton
class QueueServer(object):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.manager = None
        self.running = None
        self.pool = []

    @staticmethod
    def register(queue_name):
        queue = Queue.Queue()
        QueueManager.register(queue_name, callable=lambda: queue)

    def auto_register(self, queue_pool_count=10):
        self.register("master_input_queue")
        self.register("master_output_queue")
        for i in range(queue_pool_count):
            random_string = get_random(16)
            input_queue_name = "{}_inputQueue".format(random_string)
            output_queue_name = "{}_outputQueue".format(random_string)
            self.register(input_queue_name)
            self.register(output_queue_name)
            self.pool.append({"QueueName": random_string, "status": 0,
                              "inputQueueName": input_queue_name,
                              "outputQueueName": output_queue_name})  # 0 is idle

    def start(self):
        self.running = True
        self.manager = QueueManager(address=('localhost', 5000), authkey=b'abc')
        self.manager.start()

    def stop(self):
        self.running = False
        if self.manager:
            self.manager.shutdown()
            self.manager.join()

    def get_queue(self, queue_name):
        if self.manager:
            return getattr(self.manager, queue_name)()
        else:
            raise Exception("get Queue {} failed, because of QueueServer is not init.".format(queue_name))

    def apply_queue(self):
        for queue in self.pool:
            if queue["status"] == 0:
                # if idel , return this queue , and update status to 1
                queue.update({"status": 1})
                return queue["inputQueueName"], queue["outputQueueName"]
        raise Exception("QueuePool has not a idle queue.")

    def release_queue(self, queue_name):
        for queue in self.pool:
            if queue["QueueName"] == queue_name:
                if queue["status"] == 1:
                    queue.update({"status": 0})
                else:
                    raise Exception("Queue relase failed, it is already idle.")
        raise Exception("QueuePool has not this queue {}.".format(queue_name))

    def status(self):
        return self.running is True
