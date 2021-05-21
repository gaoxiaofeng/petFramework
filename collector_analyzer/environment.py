from logger import Logger
from sshlibrary import SSH
import re


class Environment(object):
    def __init__(self):
        super(Environment, self).__init__()
        self.db_host = None
        self.db_ip = None
        self.lab_name = 'unkownLab'

    def precheck(self, host, root_passwd):
        self._resolve_db_host(host, root_passwd)
        self._resolve_lab_name()

    def _resolve_db_host(self, host, root_passwd):
        db_info = SSH.execute_remote_command(host,
                                             "host $(smanager.pl status service ^db$ | awk -F : '{print $2}')|grep -v -i ipv6",
                                             password=root_passwd)
        self.db_host = db_info.split(' ')[0].strip()
        self.db_ip = db_info.split(' ')[-1].strip()

    def _resolve_lab_name(self):
        labname_pattern = re.compile(r'(.+?)[vm|node].*')
        match = labname_pattern.match(self.db_host)
        if match:
            self.lab_name = match.groups()[0]
            Logger.info("Lab name: {}".format(self.lab_name))
