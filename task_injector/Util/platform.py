import collections
import json
import subprocess
import time
from os.path import exists
import traceback
from Logger import Debug
from Utility import singleton


def execute_command(command):
    command = command.strip()
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # if wait:
    #     process.wait()
    stdout = process.stdout.read()
    stdout = stdout.decode('utf-8').strip()
    stderr = process.stderr.read()
    stderr = stderr.decode('utf-8').strip()

    return stdout, stderr


def ls():
    command = "ls"
    stdout, stderr = execute_command(command)
    if stdout:
        return stdout
    else:
        raise Exception("ls failed!")


def wait_for(template_id_or_desc, number=1):
    if "defined" in template_id_or_desc:
        command = """
        echo -e "set head off;\\n set linesize 2000; \\n select 'result'||count(*) from task_info where status in (1,2) and template_id='{}';"| sqlplus -s omc/omc|grep result
        """.format(template_id_or_desc)
    else:
        command = """
        echo -e "set head off;\\n  select 'result'||count(*) from task_info INNER JOIN plan_info ON task_info.plan_id = plan_info.plan_id   where task_info.status in (1,2)  and plan_info.DESCRIPTION like '{}';"| sqlplus -s omc/omc
        """.format(template_id_or_desc)
    while 1:
        stdout, stderr = execute_command(command)
        response = stdout.replace('result', '')
        Debug.info('waitFor {}: {} < {}'.format(template_id_or_desc, response, number))
        if response.isdigit():
            num = int(response)
            if num >= number:
                Debug.info("Wait for {} 10s...".format(template_id_or_desc))
                time.sleep(10)
            else:
                break
        else:
            Debug.error("Wait for function failed: response is not digital: {}".format(response))
            time.sleep(2)


def wait_until(*template_ids):
    if len(template_ids) == 0:
        return
    elif len(template_ids) > 1:
        command = """
        echo -e "set head off;\\n  select 'result'||count(*) from task_info INNER JOIN plan_info ON task_info.plan_id = plan_info.plan_id   where task_info.status in (1,2)  and task_info.template_id in {};"| sqlplus -s omc/omc
        """.format(tuple(template_ids))
    else:
        # one tempalte
        command = """
        echo -e "set head off;\\n  select 'result'||count(*) from task_info INNER JOIN plan_info ON task_info.plan_id = plan_info.plan_id   where task_info.status in (1,2)  and task_info.template_id = '{}';"| sqlplus -s omc/omc
        """.format(template_ids[0])

    while 1:
        stdout, stderr = execute_command(command)
        response = stdout.replace('result', '')
        Debug.info('waituntil {}: {}'.format(tuple(template_ids), response))
        if response.isdigit():
            num = int(response)
            if num > 0:
                time.sleep(10)
            else:
                break
        else:
            time.sleep(2)


@singleton
class RestdaAPI(object):
    def __init__(self):
        self._fqdn = None
        self.token_expiration = 60 * 30
        self.read_token_timeout = 3600 * 2
        self.user_passwd_dict = dict()

    def issue_token(self, user, cache_file, password=None):
        if not password:
            password = self._get_password(user)
        command = """
        curl -v -k -X "POST"  "https://{fqdn}:9527/restda/oauth2/token"  -H "Content-Type:application/x-www-form-urlencoded"  -d "grant_type=client_credentials"  -u  '{user_name}:{password}'
        """.format(fqdn=self.fqdn, user_name=user, password=password)
        stdout, stderr = execute_command(command)
        try:
            response = eval(stdout)
            Debug.info(response)
        except Exception as err:
            Debug.error("Command: {}, stdout: {}, stderr: {}".format(command, stdout, stderr))
            Debug.error("Exception occur: {}".format(err))
            raise Exception("format token failed, error: {}: request: {},response: {}".format(err, command, stdout))
        if "token_key" in response:
            token = response["token_key"]
            with open(cache_file, "ab") as f:
                f.write("{}\n".format(json.dumps(collections.OrderedDict(Token=token, TimeStamp=int(time.time())))).encode('utf-8'))
            return token
        elif "errorMessage" in response:
            raise Exception(response["errorMessage"])
        else:
            raise Exception("token response unexpected: {}".format(stdout))

    def _get_password(self, user):
        if user in self.user_passwd_dict:
            return self.user_passwd_dict[user]
        else:
            command = "/opt/nokia/oss/bin/syscredacc.sh -user {user} -type appserv -instance appserv".format(user=user)
            stdout, stderr = execute_command(command)
            if stdout:
                self.user_passwd_dict.update({user: stdout})
                return stdout
            else:
                raise Exception("get {} Password failed!".format(user))

    @property
    def fqdn(self):
        if not self._fqdn:
            # command = "/opt/cpf/bin/cpf_list_lb_address.sh --lb was"
            command = "host $(smanager.pl status service restda$|awk -F : '{print $2}')|head -n 1|awk '{print $1}'"
            stdout, stderr = execute_command(command)
            if stdout:
                self._fqdn = stdout
            else:
                raise Exception("get LBwas failed!")
        return self._fqdn

    def read_token(self, cache_file):
        start_time = time.time()
        while 1:
            if time.time() - start_time > self.read_token_timeout:
                raise Exception("read token timeout in {}".format(self.read_token_timeout))
            if exists(cache_file):
                with open(cache_file, "rb") as f:
                    lines = f.readlines()
                    lines = list(map(lambda line: line.decode('utf-8'),lines))
                if lines:
                    last_line = lines[-1]
                    try:
                        token_map = eval(last_line)
                        token = token_map["Token"]
                        time_stamp = token_map["TimeStamp"]
                        if time.time() - time_stamp < self.token_expiration:
                            return token
                    except Exception as err:
                        Debug.error("Read Token failed, err: {}. {}".format(err, traceback.format_exc()))
            time.sleep(10)
            Debug.info('read token failed, next in 10 s')

    def query_plans(self, token):
        command = """
        curl  -v -k -H "Authorization:Bearer {token}"  -X "GET" "https://{fqdn}:9527/restda/api/v1/plans/"
        """.format(token=token, fqdn=self.fqdn)
        stdout, stderr = execute_command(command)
        response = eval(stdout)
        if "totalCountOfPlan" in response and "planInformations" in response:
            return response["totalCountOfPlan"]
        elif "errorMessage" in response:
            raise Exception(response["errorMessage"])
        else:
            raise Exception(stdout)

    def query_tasks(self, token):
        command = """
        curl  -v -k -H "Authorization:Bearer {token}"  -X "GET" "https://{fqdn}:9527/restda/api/v1/tasks/"
        """.format(token=token, fqdn=self.fqdn)
        stdout, stderr = execute_command(command)
        response = eval(stdout)
        if "totalCountOfTask" in response and "taskInformations" in response:
            return response["totalCountOfTask"]
        elif "errorMessage" in response:
            raise Exception(response["errorMessage"])
        else:
            raise Exception(stdout)

    def qurey_templates(self, token):
        command = """
        curl  -v -k -H "Authorization:Bearer {token}"  -X "GET" "https://{fqdn}:9527/restda/api/v1/templates"
        """.format(token=token, fqdn=self.fqdn)
        stdout, stderr = execute_command(command)
        response = eval(stdout)
        if "countOfTemplates" in response and "templateInformation" in response:
            return response["countOfTemplates"]
        elif "errorMessage" in response:
            raise Exception(response["errorMessage"])
        else:
            raise Exception(stdout)

    def create_plan(self, token, json):
        command = """
        curl -v -k -H "Authorization:Bearer {token}" -X "POST"  "https://{fqdn}:9527/restda/api/v1/plans"  -H "Content-Type:application/json"  --data '{json}'
        """.format(token=token, fqdn=self.fqdn, json=json)
        stdout, stderr = execute_command(command)
        response = eval(stdout)
        if "status" in response:
            Debug.info("create plan request: {} response: {}".format(command, response))
            assert response["status"] == "success", "Create A plan failed , because Response is {}".format(stdout)
        elif "errorMessage" in response:
            Debug.error("create plan request: {} response: {}".format(command, response))
            raise Exception(response["errorMessage"])
        else:
            Debug.error("create plan request: {} response: {}".format(command, response))
            raise Exception(stdout)
