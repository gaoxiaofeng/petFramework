#!/usr/bin/env python
# coding=utf-8
from args import args_parser, args_check
from logger import Logger
from tables import FmAlarm, Topology
from os.path import abspath, dirname, join
from engine import summary, count_from_leveldb, export_from_leveldb, import_alarm_to_leveldb, \
    import_topology_to_leveldb, head_from_leveldb, \
    delete_from_leveldb, get_from_leveldb, destroy_leveldb, clean_from_leveldb, compact_leveldb, repair_leveldb
from variable import *

if __name__ == "__main__":
    options = args_parser()
    if options.debug:
        Logger.enable_debug()
    args_check(options)
    if options.operation == "summary":
        if options.dbpath:
            summary(options.dbpath, write_mode=options.write_mode)
        elif options.cluster == CLUSTER_FM:
            summary(FMALARM_DB, write_mode=options.write_mode)
        elif options.cluster == CLUSTER_TOPOLOGY:
            summary(TOPOLOGY_DB, write_mode=options.write_mode)
    elif options.operation == "export":
        if options.outputfolder:
            target_file = join(options.outputfolder, '{}.csv'.format(options.cluster))
        else:
            target_file = join(dirname(abspath(__file__)), '{}.csv'.format(options.cluster))
        if options.dbpath:
            export_from_leveldb(options.dbpath, target_file, include=options.include, exclude=options.exclude,
                                column=[], write_mode=options.write_mode, limit=options.limit)
        elif options.cluster == CLUSTER_FM:
            export_from_leveldb(FMALARM_DB, target_file, include=options.include, exclude=options.exclude,
                                column=FmAlarm.column_name, write_mode=options.write_mode, limit=options.limit)
        elif options.cluster == CLUSTER_TOPOLOGY:
            export_from_leveldb(TOPOLOGY_DB, target_file, include=options.include, exclude=options.exclude,
                                column=Topology.column_name, write_mode=options.write_mode, limit=options.limit)
    elif options.operation == "import":
        if options.dbpath:
            Logger.error("--dbpath is not supported")
        elif options.cluster == CLUSTER_FM:
            import_alarm_to_leveldb(FMALARM_DB, options.srcfile, write_mode=options.write_mode)
        elif options.cluster == CLUSTER_TOPOLOGY:
            import_topology_to_leveldb(TOPOLOGY_DB, options.srcfile, write_mode=options.write_mode)
    elif options.operation == "count":
        if options.dbpath:
            count_from_leveldb(options.dbpath, include=options.include, exclude=options.exclude,
                               write_mode=options.write_mode)
        elif options.cluster == CLUSTER_FM:
            count_from_leveldb(FMALARM_DB, include=options.include, exclude=options.exclude,
                               write_mode=options.write_mode)
        elif options.cluster == CLUSTER_TOPOLOGY:
            count_from_leveldb(TOPOLOGY_DB, include=options.include, exclude=options.exclude,
                               write_mode=options.write_mode)
    elif options.operation == "head":
        limitation = options.limit if options.limit else 5
        if options.dbpath:
            head_from_leveldb(options.dbpath, column=[], limitation=limitation, include=options.include,
                              exclude=options.exclude,
                              write_mode=options.write_mode, external_format=options.format, internal_db=False)
        elif options.cluster == CLUSTER_FM:
            head_from_leveldb(FMALARM_DB, column=FmAlarm.column_name, limitation=limitation, include=options.include,
                              exclude=options.exclude,
                              write_mode=options.write_mode, external_format=options.format)
        elif options.cluster == CLUSTER_TOPOLOGY:
            head_from_leveldb(TOPOLOGY_DB, column=Topology.column_name, limitation=limitation, include=options.include,
                              exclude=options.exclude,
                              write_mode=options.write_mode, external_format=options.format)
    elif options.operation == "delete":
        if options.dbpath:
            delete_from_leveldb(options.dbpath, options.key, write_mode=options.write_mode)
        elif options.cluster == CLUSTER_FM:
            delete_from_leveldb(FMALARM_DB, options.key, write_mode=options.write_mode)
        elif options.cluster == CLUSTER_TOPOLOGY:
            delete_from_leveldb(TOPOLOGY_DB, options.key, write_mode=options.write_mode)
    elif options.operation == "get":
        if options.dbpath:
            Logger.error("--dbpath is not supported")
        elif options.cluster == CLUSTER_FM:
            get_from_leveldb(FMALARM_DB, options.key, column=FmAlarm.column_name, external_format=options.format,
                             write_mode=options.write_mode)
        elif options.cluster == CLUSTER_TOPOLOGY:
            get_from_leveldb(TOPOLOGY_DB, options.key, column=Topology.column_name, external_format=options.format,
                             write_mode=options.write_mode)
    elif options.operation == "clean":
        if options.dbpath:
            clean_from_leveldb(options.dbpath, include=options.include, exclude=options.exclude,
                               write_mode=options.write_mode)
        elif options.cluster == CLUSTER_FM:
            clean_from_leveldb(FMALARM_DB, include=options.include, exclude=options.exclude,
                               write_mode=options.write_mode)
        elif options.cluster == CLUSTER_TOPOLOGY:
            clean_from_leveldb(TOPOLOGY_DB, include=options.include, exclude=options.exclude,
                               write_mode=options.write_mode)
    elif options.operation == "destroy":
        if options.dbpath:
            destroy_leveldb(options.dbpath)
        elif options.cluster == CLUSTER_FM:
            destroy_leveldb(FMALARM_DB)
        elif options.cluster == CLUSTER_TOPOLOGY:
            destroy_leveldb(TOPOLOGY_DB)

    elif options.operation == "compact":
        if options.dbpath:
            compact_leveldb(options.dbpath, write_mode=options.write_mode)
        elif options.cluster == CLUSTER_FM:
            compact_leveldb(FMALARM_DB, write_mode=options.write_mode)
        elif options.cluster == CLUSTER_TOPOLOGY:
            compact_leveldb(TOPOLOGY_DB, write_mode=options.write_mode)

    elif options.operation == "repair":
        if options.dbpath:
            repair_leveldb(options.dbpath)
        elif options.cluster == CLUSTER_FM:
            repair_leveldb(FMALARM_DB)
        elif options.cluster == CLUSTER_TOPOLOGY:
            repair_leveldb(TOPOLOGY_DB)