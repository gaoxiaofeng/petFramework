import sys
import shutil

try:
    from os.path import abspath, dirname, join

    if sys.version_info.major == 3:
        so_source = join(dirname(abspath(__file__)),
                         "leveldb.{}{}".format(sys.version_info.major, sys.version_info.minor))
    elif sys.version_info.major == 2:
        so_source = join(dirname(abspath(__file__)),
                         "leveldb.{}{}".format(sys.version_info.major, sys.version_info.minor))
    else:
        raise ImportError("python release is not support: {}.{}".format(sys.version_info.major, sys.version_info.minor))
    so_target = join(dirname(abspath(__file__)), "leveldb.so")
    shutil.copy2(so_source, so_target)
    import leveldb
except ImportError as e:
    print("import leveldb failed: {}".format(e))
    exit(1)
from os.path import exists, isdir
import shutil
from logger import Logger
import collections
import json
import time
from variable import *
from subprocess import Popen, PIPE
import shlex


def convert_to_str(content):
    if sys.version_info.major == 3:
        content = content.decode('utf-8') if isinstance(content, (bytes, bytearray)) else content
    return content


def convert_to_leveldb_format(content):
    if sys.version_info.major == 3:
        content = bytearray(content, 'utf-8') if isinstance(content, str) else content
    return content


def execute_command(command):
    command = command.strip()
    process = Popen(command, shell=True, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    stdout = stdout.strip()
    stderr = stderr.strip()
    rc = process.returncode
    if rc:
        Logger.debug("stdout: {}".format(stdout))
        Logger.debug("stderr: {}".format(stderr))
        Logger.debug("rc: {}".format(rc))
    return stdout, stderr, rc


class LevelDB(object):
    def __init__(self, db_path, write_mode):
        super(LevelDB, self).__init__()
        self.db_path = db_path
        self.write_mode = write_mode
        self._db = None

    @property
    def db(self):
        if self.write_mode:
            if not self._db:
                Logger.debug("loading {}".format(self.db_path))
                self._db = leveldb.LevelDB(self.db_path, paranoid_checks=True)
                Logger.debug("loaded {}".format(self.db_path))
        else:
            db_path_copy = "{}_copy".format(self.db_path)
            self.delete_db(db_path_copy)
            Logger.debug("deleted {}".format(db_path_copy))
            self.copy_db(self.db_path, db_path_copy)
            Logger.debug("copied {}".format(db_path_copy))
            if not self._db:
                Logger.debug("loading {}".format(db_path_copy))
                self._db = leveldb.LevelDB(db_path_copy, paranoid_checks=True)
                Logger.debug("loaded {}".format(db_path_copy))
        return self._db

    @staticmethod
    def delete_db(db_path):
        if exists(db_path) and isdir(db_path):
            rm_status = True
            for i in range(3):
                try:
                    shutil.rmtree(db_path)
                except Exception as err:
                    rm_status = False
                    time.sleep(1)
                else:
                    rm_status = True
                    break
            if not rm_status:
                Logger.error("remove {} failed in 3 times".format(db_path))
                exit(1)

    @staticmethod
    def copy_db(source_db_path, target_db_path):
        command = "cp -r {src} {dst}".format(src=source_db_path, dst=target_db_path)
        stdout, stderr, rc = execute_command(command)
        if rc:
            Logger.error(stderr)
            exit(1)

    def count(self, include=None, exclude=None):
        row_count = 0
        rows = self.db.RangeIter()
        for row in rows:
            key = row[0]
            value = row[1]
            if include and not self._match_include_rule(value, include):
                # not matched include rule
                continue
            if exclude and self._match_include_rule(value, exclude):
                # not matched exclude rule
                continue
            row_count += 1
        return row_count

    def head(self, limitation=5, include=None, exclude=None):
        head_rows = []
        rows = self.db.RangeIter()
        if limitation:
            for index, row in enumerate(rows):
                if len(head_rows) >= limitation:
                    break
                key = row[0]
                value = row[1]
                if include and not self._match_include_rule(value, include):
                    # not matched include rule
                    continue
                if exclude and self._match_include_rule(value, exclude):
                    # not matched exclude rule
                    continue
                head_rows.append((key, value))
            return head_rows
        else:
            Logger.error("head limitation: {} is invalid".format(limitation))

    def import_csv_to_leveldb(self, srcfile, first_column_name):
        rows = []
        write_batch = 1000
        with open(srcfile, "r") as f:
            line = f.readline().strip()
            if line and not line.startswith(first_column_name):
                # is not column
                key = self.split_line_by_comma(line)[0]
                value = convert_to_leveldb_format(LEVELDB_SEPARATER).join(self.split_line_by_comma(line))
                _row = (key, value)
                self.write([_row])
            while line is not None and line != '':
                line = f.readline().strip()
                if line:
                    key = self.split_line_by_comma(line)[0]
                    value = convert_to_leveldb_format(LEVELDB_SEPARATER).join(self.split_line_by_comma(line))
                    _row = (key, value)
                    rows.append(_row)
                    if len(rows) > write_batch:
                        self.write(rows)
                        rows = []
            if rows:
                self.write(rows)

    @staticmethod
    def split_line_by_comma(line):
        _line = shlex.shlex(line)
        _line.whitespace = ','
        _line.whitespace_split = True
        items = list(_line)
        return list(map(lambda item: convert_to_leveldb_format(item.strip('"').strip("'")), items))

    def export(self, file_path, include=None, exclude=None, column=None, limit=0):
        rows = self.db.RangeIter()
        if include:
            Logger.debug("include rule: {}".format(include))
        if exclude:
            Logger.debug("exclude rule: {}".format(exclude))
        with open(file_path, 'w') as f:
            if column:
                f.write("{}\n".format(','.join(column)))
            count = 0
            for index, row in enumerate(rows):
                if limit and count >= limit:
                    break
                # row[0] is key, row[1] is value
                value = row[1]
                if include and not self._match_include_rule(value, include):
                    # not matched include rule
                    continue
                if exclude and self._match_include_rule(value, exclude):
                    # not matched exclude rule
                    continue
                value = convert_to_str(value).replace(convert_to_str(LEVELDB_SEPARATER), ",")
                value = "{}\n".format(value)
                f.write(value)
                count += 1
            Logger.info("exported rows: {}".format(count))

    def clean(self, include=None, exclude=None):
        rows = self.db.RangeIter()
        delete_row_count = 0
        if include:
            Logger.debug("include rule: {}".format(include))
        if exclude:
            Logger.debug("exclude rule: {}".format(exclude))
        for row in rows:
            # row[0] is key, row[1] is value
            key = row[0]
            value = row[1]
            if include and not self._match_include_rule(value, include):
                # not matched include rule
                continue
            if exclude and self._match_include_rule(value, exclude):
                # not matched exclude rule
                continue
            self.delete(key)
            delete_row_count += 1
        Logger.info("Clean count: {}".format(delete_row_count))

    @staticmethod
    def _match_include_rule(line, include_rule):
        line = convert_to_str(line)
        rule_match = []
        for _rule in include_rule.split("OR"):
            __rule_match = all([__rule in line for __rule in _rule.split("AND")])
            rule_match.append(__rule_match)
        return any(rule_match)

    def get_count(self):
        rows_count = sum(1 for _ in self.db.RangeIter())
        Logger.debug("leveldb rows count: {}".format(rows_count))
        return rows_count

    def repair_db(self):
        leveldb.RepairDB(self.db_path)

    def destroy_db(self):
        leveldb.DestroyDB(self.db_path)

    def init_db(self):
        self.db.RangeIter()

    def get_value(self, specified_key):
        try:
            specified_key = convert_to_leveldb_format(specified_key)
            value = self.db.Get(specified_key, verify_checksums=True)
        except Exception as err:
            Logger.warning("key: ({}) is not exist".format(specified_key))
            exit(1)
        else:
            return value

    def write(self, rows):
        batch = leveldb.WriteBatch()
        for row in rows:
            batch.Put(row[0], row[1])
        self.db.Write(batch)

    def delete(self, key):
        self.db.Delete(convert_to_leveldb_format(key))

    def compact(self):
        self.db.CompactRange()

    def summary(self):
        return self.db.GetStats()

    def close(self):
        if not self.write_mode:
            db_path_copy = "{}_copy".format(self.db_path)
            self.delete_db(db_path_copy)


def count_from_leveldb(db_path, include=None, exclude=None, write_mode=False):
    _db = LevelDB(db_path, write_mode)
    row_count = _db.count(include=include, exclude=exclude)
    print("count:{}".format(convert_to_str(row_count)))
    _db.close()


def head_from_leveldb(db_path, column, limitation, include=None, exclude=None, write_mode=False,
                      external_format=FORMAT_ORIGINAL, internal_db=True):
    _db = LevelDB(db_path, write_mode)
    rows = _db.head(limitation=limitation, include=include, exclude=exclude)
    if internal_db:
        _print_rows(rows, column=column, external_format=external_format)
    else:
        _print_rows(rows, external_format=FORMAT_VISUALIZE)
    _db.close()


def _print_rows(rows, column=[], external_format=FORMAT_ORIGINAL):
    for row in rows:
        if external_format == FORMAT_ORIGINAL:
            print("| {:^20} | {:^80} |".format(convert_to_str(row[0]), convert_to_str(row[1])))
        elif external_format == FORMAT_VISUALIZE:
            print("| {:^20} | {:^80} |".format(convert_to_str(row[0]),
                                               convert_to_str(row[1].replace(LEVELDB_SEPARATER, "&".encode('utf-8')))))
        elif external_format == FORMAT_PRETTY:
            data = row[1].split(LEVELDB_SEPARATER)
            data = list(map(lambda d: convert_to_str(d), data))
            print("{}".format(json.dumps(collections.OrderedDict(zip(column, data)), indent=4, ensure_ascii=False)))


def get_from_leveldb(db_path, key, column, external_format=FORMAT_ORIGINAL, write_mode=False):
    _db = LevelDB(db_path, write_mode)
    value = _db.get_value(key)
    print("{}".format("*" * 110))
    if external_format == FORMAT_ORIGINAL:
        print("| {:^20} | {:^80} |".format(convert_to_str(key), convert_to_str(value)))
    elif external_format == FORMAT_VISUALIZE:
        print("| {:^20} | {:^80} |".format(convert_to_str(key), convert_to_str(value.replace(LEVELDB_SEPARATER, "&"))))
    elif external_format == FORMAT_PRETTY:
        data = value.split(LEVELDB_SEPARATER)
        data = list(map(lambda d: convert_to_str(d), data))
        print("{}".format(json.dumps(collections.OrderedDict(zip(column, data)), indent=4, ensure_ascii=False)))
    print("{}".format("*" * 110))
    _db.close()


def delete_from_leveldb(db_path, key, write_mode=False):
    _db = LevelDB(db_path, write_mode)
    _db.delete(key)
    _db.close()


def export_from_leveldb(db_path, target_csv_file, include=None, exclude=None, column=None, write_mode=False, limit=0):
    _db = LevelDB(db_path, write_mode)
    _db.export(target_csv_file, include=include, exclude=exclude, column=column, limit=limit)
    _db.close()
    Logger.info("exported file: {}".format(target_csv_file))


def import_csv_to_leveldb(db_path, srcfile, first_column_name, write_mode=False):
    _db = LevelDB(db_path, write_mode)
    _db.import_csv_to_leveldb(srcfile, first_column_name)
    _db.close()
    Logger.info("imported file: {} to {}".format(srcfile, db_path))


def import_alarm_to_leveldb(db_path, srcfile, write_mode=False):
    import_csv_to_leveldb(db_path, srcfile, "alarm_id", write_mode=write_mode)


def import_topology_to_leveldb(db_path, srcfile, write_mode=False):
    import_csv_to_leveldb(db_path, srcfile, "DN", write_mode=write_mode)


def summary(db_path, write_mode=False):
    _db = LevelDB(db_path, write_mode)
    stats = _db.summary()
    _db.close()
    Logger.info(stats)


def clean_from_leveldb(db_path, include=None, exclude=None, write_mode=False):
    _db = LevelDB(db_path, write_mode)
    _db.clean(include=include, exclude=exclude)
    _db.close()
    Logger.info("Clean: {} successful".format(db_path))


def destroy_leveldb(db_path):
    leveldb.DestroyDB(db_path)
    Logger.info("Destroy leveldb: {}".format(db_path))


def compact_leveldb(db_path, write_mode=False):
    _db = LevelDB(db_path, write_mode)
    _db.compact()
    _db.close()
    Logger.info("Compact leveldb: {}.".format(db_path))


def repair_leveldb(db_path):
    leveldb.RepairDB(db_path)
    Logger.info("Repair leveldb: {}.".format(db_path))
