import traceback

from Logger import Log
from MasterClient import MasterClient
from MasterServer import MasterServer
from Utility import *
from Variable import *


def collect_message(func):
    def wapper(self, *args, **kwargs):
        try:
            result = func(self, *args, **kwargs)
            return result
        except Exception as err:
            Log().error(traceback.format_exc())
            raise Exception(err)

    return wapper


class BaseHandler(object):
    def __init__(self):
        super(BaseHandler, self).__init__()
        self.successor = None

    def handle(self, **kwargs):
        if self.successor:
            self.successor.handle(**kwargs)


class InitEnv(BaseHandler):
    def __init__(self):
        super(InitEnv, self).__init__()

    @collect_message
    def handle(self, **kwargs):
        Log().info("@[{}]".format(self.__class__.__name__))
        single = kwargs["single"]
        operation = kwargs["operation"]
        mkdir(CACHE_DIR)
        if single and operation == "start":
            clean_folder(CACHE_DIR)
            remove(CACHE_FILE)
            Log().info("cleaning data folder")
        super(InitEnv, self).handle(**kwargs)


# class cleanEnv(BaseHandler):
#     def __init__(self):
#         super(cleanEnv, self).__init__()
#     def handle(self,**kwargs):
#         Log().info("@[%s]" % self.__class__.__name__)
#         cache = kwargs["cache"]
#         cleanFolder(cache)
#         super(cleanEnv,self).handle(**kwargs)

class StartMaster(BaseHandler):
    def __init__(self):
        super(StartMaster, self).__init__()

    def handle(self, **kwargs):
        Log().info("@[{}]".format(self.__class__.__name__))
        scenario = kwargs["scenario"]
        if not is_open("localhost", 5000):
            # Master server is not running, will do start.
            Log().info("Master Server starting... ")
            master_server = MasterServer()
            master_server.set_scenario(scenario)
            master_server.start()
        else:
            Log().info("Master Server already started.")
        super(StartMaster, self).handle(**kwargs)


class AttachMaster(BaseHandler):
    def __init__(self):
        super(AttachMaster, self).__init__()

    def handle(self, **kwargs):
        Log().info("@[{}]".format(self.__class__.__name__))
        master_client = MasterClient()

        if kwargs["operation"]:
            master_client.start(console=False)
            operation = kwargs["operation"]
            if operation == "start":
                output = master_client.one_click_start()
                Log().info(output)
            elif operation == "stop":
                output = master_client.one_click_stop()
                Log().info(output)
            elif operation == "result":
                output = master_client.one_click_result()
                Log().info(output)
            elif operation == "check":
                output = master_client.one_click_check()
                Log().info(output)
            elif operation == "clean":
                output = master_client.one_click_clean()
                Log().info(output)
            elif operation == "exit":
                output = master_client.one_click_exit()
                Log().info(output)
            else:
                pass
            master_client.stop()
        else:
            # start console
            master_client.start()

        super(AttachMaster, self).handle(**kwargs)


class StopMaster(BaseHandler):
    def __init__(self):
        super(StopMaster, self).__init__()

    def handle(self, **kwargs):
        Log().info("@[{}]".format(self.__class__.__name__))
        super(StopMaster, self).handle(**kwargs)
