import subprocess
import os
from os.path import exists, isfile


def singleton(cls, *args, **kwargs):
    instances = dict()

    def _singleton():
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return _singleton


def execute_command(command):
    command = command.strip()
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout = process.stdout.read()
    stdout = stdout.strip()
    stderr = process.stderr.read()
    stderr = stderr.strip()

    return stdout, stderr


def remove_file(path):
    if exists(path) and isfile(path):
        os.remove(path)
