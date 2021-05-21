import subprocess
import logging


class Logger(object):
    logger = logging.getLogger("Logger")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s: %(message)s')
    # handler = logging.FileHandler(join(dirname(abspath(__file__)), 'prepare.log'))
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    @classmethod
    def info(cls, message):
        message = message.strip()
        cls.logger.info(message)

    @classmethod
    def error(cls, message):
        message = message.strip()
        cls.logger.error(message)
        print message

    @classmethod
    def debug(cls, message):
        message = message.strip()
        cls.logger.debug(message)

    @classmethod
    def warning(cls, message):
        message = message.strip()
        cls.logger.warning(message)


def execute_command(command):
    command = command.strip()
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout = process.stdout.read()
    stdout = stdout.decode('utf-8').strip()
    stderr = process.stderr.read()
    stderr = stderr.decode('utf-8').strip()
    return stdout, stderr


class Zabbix(object):
    def __init__(self):
        super(Zabbix, self).__init__()

    @staticmethod
    def _get_all_hosts():
        vms = []
        stdout, stderr = execute_command("smanager.pl status|grep -v standAlone")
        for line in stdout.split("\n"):
            if 'node' in line or 'vm' in line:
                vms.append(line.strip())
        return vms

    @staticmethod
    def _generate_fix_script():
        shells = ["mkdir /var/run/zabbix", "chown zabbix:zabbix /var/run/zabbix", "/etc/init.d/zabbix-agent restart"]
        with open("/home/omc/fix_zabbix.sh", 'wb') as f:
            f.write('\n'.join(shells).encode('utf-8'))

    @staticmethod
    def _fix_zabbix(host):
        Logger.info("fix {}".format(host))
        stdout, stderr = execute_command("ssh root@{host} sh /home/omc/fix_zabbix.sh".format(host=host))
        Logger.debug(stdout)
        Logger.warning(stderr)

    @classmethod
    def fix_zabbix(cls):
        cls._generate_fix_script()
        hosts = cls._get_all_hosts()
        for host in hosts:
            cls._fix_zabbix(host)


if __name__ == '__main__':
    Zabbix.fix_zabbix()
