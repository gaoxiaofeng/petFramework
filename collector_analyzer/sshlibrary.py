#!/usr/bin/env python
import paramiko
from logger import Logger


class SSH(object):
    def __init__(self):
        super(SSH, self).__init__()

    @staticmethod
    def scp(host, source_file, dest_file, port=22, username='root', password='arthur'):
        try:
            t = paramiko.Transport((host, port))
            t.connect(username=username, password=password)
            sftp = paramiko.SFTPClient.from_transport(t)
            sftp.get(source_file, dest_file)
        except Exception as err:
            Logger.error('scp {}:{} to {} failed, reason: {}'.format(host, source_file, dest_file, err))
        finally:
            t.close()

    @staticmethod
    def execute_remote_command(host, command, port=22, username='root', password='arthur'):
        try:
            client = paramiko.SSHClient()
            # client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(host, port=port, username=username, password=password)
            stdin, stdout, stderr = client.exec_command(command)
            return stdout.read().decode('utf-8')
        finally:
            client.close()


if __name__ == '__main__':
    result = SSH.execute_remote_command("10.32.192.144", 'hostname')
    print(result)
