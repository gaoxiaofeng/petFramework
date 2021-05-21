#!/usr/bin/env python
# coding=utf-8
DNLIST_DB = "/var/opt/oss/Nokia-restda-fm/leveldb/level-db-dnList"
FMALARM_DB = "/var/opt/oss/Nokia-restda-fm/leveldb/level-db-fmAlarm"
TOPOLOGY_DB = "/var/opt/oss/Nokia-restda-fm/leveldb/level-db-topology"
WS_DB = "/var/opt/oss/Nokia-restda-fm/leveldb/level-db-ws-help-info"

ARGS_MISSING_ERR = "Please specific script argument: {}"
SRC_IS_NOT_ABSPATH = "srcfile path: {} is not absolute path"
SRC_IS_NOT_FILE = "srcfile path: {} is not a file"
OUTPUT_IS_NOT_DIR = "output path: {} is not a directory"

CLUSTER_FM = "fm"
CLUSTER_TOPOLOGY = "topology"

FORMAT_ORIGINAL = "original"
FORMAT_VISUALIZE = "visualize"
FORMAT_PRETTY = "pretty"

LEVELDB_SEPARATER = u'\u200e'.encode('utf-8')
