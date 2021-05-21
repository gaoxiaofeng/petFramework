#!/usr/bin/env python
# coding=utf-8
import optparse
import os
from logger import Logger
from variable import *


def args_parser():
    opt = optparse.OptionParser(version="1.5.3")
    operation_choice = ('summary', 'count', 'head', 'get', 'delete', 'clean', 'export', 'import', 'destroy', 'compact', 'repair')
    cluster_choice = (CLUSTER_FM, CLUSTER_TOPOLOGY)
    format_choice = (FORMAT_ORIGINAL, FORMAT_VISUALIZE, FORMAT_PRETTY)
    opt.add_option("--operation", action='store', help="operation of leveldb, allow: {}".format(operation_choice),
                   dest="operation", choices=operation_choice)
    opt.add_option("--cluster", action='store', help="cluster of operation, allow: {}".format(cluster_choice),
                   dest="cluster", choices=cluster_choice)
    opt.add_option("--dbpath", action='store', help="db path for all operation", dest="dbpath")
    opt.add_option("--key", action='store', help="specified key for get/delete operation", dest="key")
    opt.add_option("--include", action='store', help="include string for count/head/export/clean operation, such as: xxANDxxORxx",
                   dest="include")
    opt.add_option("--exclude", action='store', help="exclude string for count/head/export/clean operation, such as: xxANDxxORxx",
                   dest="exclude")
    opt.add_option("--limit", action='store', help="limit rows for head/export operation", dest="limit", type=int, default=0)
    opt.add_option("--srcfile", action='store', help="resource file for import operation", dest="srcfile")
    opt.add_option("--outputfolder", action='store', help="output folder for export operation", dest="outputfolder")
    opt.add_option("--format", action='store', help="format mode, allow: {}".format(format_choice), dest="format", choices=format_choice, default=format_choice[0])
    opt.add_option("--writemode", action='store_true', help="write mode, operate db directly.", dest="write_mode")
    opt.add_option("--debug", action='store_true', help="debug level", dest="debug", default=False)
    _options, _args = opt.parse_args()
    return _options


def args_check(options):
    if options.write_mode and os.getuid() != 579:
        Logger.error("current user must be restda!")
        Logger.info('tips: runuser restda -s "/bin/sh" -c "python leveldb_ops.py -h"')
        exit(1)
    if not options.operation:
        Logger.error(ARGS_MISSING_ERR.format("--operation"))
        exit(1)
    if options.operation in ('summary', 'count', 'head', 'get', 'delete', 'clean', 'export', 'import', 'destroy', 'compact') and not options.cluster and not options.dbpath:
        Logger.error(ARGS_MISSING_ERR.format("--cluster or --dbpath"))
        exit(1)
    if options.srcfile:
        if not os.path.isabs(options.srcfile):
            Logger.error(SRC_IS_NOT_ABSPATH.format(options.srcfile))
            exit(1)
        if not (os.path.exists(options.srcfile) and os.path.isfile(options.srcfile)):
            Logger.error(SRC_IS_NOT_FILE.format(options.srcfile))
            exit(1)
    if options.outputfolder:
        if not (os.path.exists(options.outputfolder) and os.path.isdir(options.outputfolder)):
            Logger.error(OUTPUT_IS_NOT_DIR.format(options.outputfolder))
            exit(1)
    if options.operation == "import":
        if not options.write_mode:
            Logger.error(ARGS_MISSING_ERR.format("--writemode"))
            exit(1)
        if not options.srcfile:
            Logger.error(ARGS_MISSING_ERR.format("--srcfile"))
            exit(1)
    elif options.operation == "get":
        if options.key is None:
            Logger.error(ARGS_MISSING_ERR.format("--key"))
            exit(1)
    elif options.operation == "delete":
        if not options.write_mode:
            Logger.error(ARGS_MISSING_ERR.format("--writemode"))
            exit(1)
        if options.key is None:
            Logger.error(ARGS_MISSING_ERR.format("--key"))
            exit(1)
    elif options.operation in ("destroy", "repair"):
        if not options.write_mode:
            Logger.error(ARGS_MISSING_ERR.format("--writemode"))
            exit(1)
    elif options.operation == "clean":
        if not options.write_mode:
            Logger.error(ARGS_MISSING_ERR.format("--writemode"))
            exit(1)
