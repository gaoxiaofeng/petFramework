from os.path import abspath, dirname, join

VERSION = '1.0'
PRINT_RED = "\033[31m"
PRINT_GREEN = "\033[32m"
PRINT_YELLOW = "\033[33m"
PRINT_END = "\033[0m"

NOT_START = "not_start"
STARTING = "starting"
STARTED = "started"
STOPPING = "stopping"
STOPED = "stoped"
OFFLINE = "offline"
CRASH = "crash"

DO_STOP = "do_stop"
DO_START = "do_start"

PASS = "pass"
FAIL = "fail"

ROOT_DIR = dirname(abspath(__file__))
CACHE_DIR = join(ROOT_DIR, "data")
CACHE_FILE = join(CACHE_DIR, "system.cache")
CASE_CACHE_FILE = join(CACHE_DIR, "case.cache")
REPORT_DIR = join(ROOT_DIR, "Report")
LOG_DIR = join(ROOT_DIR, "log")
LOG_FILE = join(LOG_DIR, "debug.log")
