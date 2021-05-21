import logging
from os.path import join


class Logger(object):
    logger = logging.getLogger("Logger")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s: %(message)s')
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    error_count = 0

    @classmethod
    def info(cls, message):
        message = message.strip()
        cls.logger.info(message)

    @classmethod
    def error(cls, message):
        message = message.strip()
        cls.logger.error(message)
        cls.error_count += 1

    @classmethod
    def debug(cls, message):
        message = message.strip()
        cls.logger.debug(message)

    @classmethod
    def warning(cls, message):
        message = message.strip()
        cls.logger.warning(message)

    @classmethod
    def set_debug_level(cls):
        cls.logger.setLevel(logging.DEBUG)

    @classmethod
    def set_info_level(cls):
        cls.logger.setLevel(logging.INFO)

    @classmethod
    def has_error(cls):
        return cls.error_count > 0

    @classmethod
    def enable_log_file(cls, log_dir):
        log_file = join(log_dir, 'analysis_data.log')
        formatter = logging.Formatter('%(asctime)s %(levelname)-8s: %(message)s')
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        cls.logger.addHandler(file_handler)
