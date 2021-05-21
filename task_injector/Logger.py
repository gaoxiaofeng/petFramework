import logging
import sys

from Utility import singleton
from Variable import *


@singleton
class Log(object):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.logger = logging.getLogger("PET Tool")
        formatter = logging.Formatter('%(levelname)-8s: %(message)s')
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def info(self, message):
        if isinstance(message, list):
            for _message in message:
                self.info(_message)
        else:
            if not isinstance(message, str):
                message = str(message)
            message = message.strip()
            self.logger.info(message)

    def error(self, message):
        if isinstance(message, list):
            for _message in message:
                self.error(_message)
        else:
            if not isinstance(message, str):
                message = str(message)
            message = message.strip()
            self.logger.error(message)

    def set_level(self, level):
        if level == "error":
            self.logger.setLevel(logging.ERROR)
        elif level == "debug":
            self.logger.setLevel(logging.DEBUG)
        elif level == "warn":
            self.logger.setLevel(logging.WARN)
        else:
            self.logger.setLevel(logging.INFO)


class Debug(object):
    logger = logging.getLogger("Debug")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s: %(message)s')
    handler = logging.FileHandler(LOG_FILE)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    @classmethod
    def info(cls, message):
        if isinstance(message, list):
            for _message in message:
                cls.info(_message)
        else:
            if not isinstance(message, str):
                message = str(message)
            message = message.strip()
            cls.logger.info(message)

    @classmethod
    def error(cls, message):
        if isinstance(message, list):
            for _message in message:
                cls.error(_message)
        else:
            if not isinstance(message, str):
                message = str(message)
            message = message.strip()
            cls.logger.error(message)
