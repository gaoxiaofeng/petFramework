import signal
import sys
from optparse import OptionParser

from Client import Client

if sys.version_info.major < 3:
    print("only support python3!")
    exit(1)


def exit_signal(sig, frame):
    pass


if __name__ == "__main__":
    signal.signal(signal.SIGINT, exit_signal)
    opt = OptionParser(version='1.0')
    opt.add_option("--operation", dest="operation", help="start,stop,check,result,clean,exit")
    opt.add_option("--single", dest="single", action='store_true')
    opt.add_option("--scenario", dest="scenario", help="enable specific scenario")
    options, args = opt.parse_args()
    if options.operation and options.operation not in ["start", "stop", "check", "result", "clean", "exit"]:
        opt.print_help()
        sys.exit(0)
    c = Client()
    c.handle(operation=options.operation, single=options.single, scenario=options.scenario)
