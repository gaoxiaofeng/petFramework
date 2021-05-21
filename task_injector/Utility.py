import os
import pickle
import random
import shutil
import socket
import sys
import time

from Variable import *


def singleton(cls, *args, **kw):
    instances = {}

    def _singleton():
        if cls not in instances:
            instances[cls] = cls(*args, **kw)
        return instances[cls]

    return _singleton


def mkdir(folder):
    if os.path.exists(folder):
        return
    error = []
    for i in range(3):
        try:
            time.sleep(1)
            os.mkdir(folder)
        except Exception as err:
            print(err)
            error.append(err)
        else:
            error.append(None)
            break
    if error and error[-1]:
        raise Exception(error[-1])


def rmtree(path):
    try:
        if os.path.exists(path) and os.path.isdir(path):
            # remove folder
            shutil.rmtree(path)
    except Exception as err:
        print(err)
        raise Exception(err)


def remove(path):
    if os.path.exists(path):
        if os.path.isfile(path):
            os.remove(path)
        else:
            rmtree(path)


def clean_folder(path):
    if os.path.exists(path):
        if os.path.isdir(path):
            # clean folder
            for fileName in os.listdir(path):
                file_path = os.path.join(path, fileName)
                remove(file_path)


def is_open(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((ip, int(port)))
        s.shutdown(2)
        return True
    except Exception as err:
        return False


class Deamon(object):
    def __init__(self):
        super(Deamon, self).__init__()
        self.running = True

    def stop(self):
        self.running = False

    def fork(self):
        try:
            pid = os.fork()
        except OSError as error:
            print('fork error: {}'.format(error))
            sys.exit(1)
        if pid == 0:
            # this is child process
            os.chdir("/")
            os.setsid()
            os.umask(0)
            # fork a Grandson process, and child process exit
            try:
                pid = os.fork()
                if pid > 0:
                    # exit child process
                    sys.exit(0)
            except OSError as error:
                print('fork error: {}'.format(error))
                sys.exit(1)
            # this is Grandson process
            self.run()
            # exit Grandson process
            sys.exit(0)
        else:
            # this is parent process . nothing to do.
            pass

    def run(self):
        pass


class Cache(object):
    def __init__(self):
        super(Cache, self).__init__()
        self.fileName = CACHE_FILE

    def save(self, obj):
        with open(self.fileName, "wb") as f:
            pickle.dump(obj=obj, file=f, protocol=2)

    def load(self):
        if os.path.exists(self.fileName):
            if os.path.isfile(self.fileName):
                with open(self.fileName, "rb") as f:
                    content = pickle.load(file=f)
                return content
            else:
                raise Exception("{} is a folder!".format(self.fileName))
        else:
            return None

    def remove(self):
        remove(self.fileName)


def get_random(length=10):
    result = []
    for i in range(length):
        result.append(random.choice("abcdefghijklmnopqrstuvwxyz"))
    return "".join(result)
