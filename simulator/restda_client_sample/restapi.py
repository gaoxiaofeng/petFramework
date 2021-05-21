#!/usr/bin/env python
import json
import logging
import requests
from requests.auth import HTTPBasicAuth
from os.path import abspath, dirname, join, exists


class Logger(object):
    logger = logging.getLogger("Logger")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s: %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    @classmethod
    def debug(cls, message):
        message = message.strip()
        cls.logger.debug(message)

    @classmethod
    def info(cls, message):
        message = message.strip()
        cls.logger.info(message)

    @classmethod
    def error(cls, message):
        message = message.strip()
        cls.logger.error(message)

    @classmethod
    def warning(cls, message):
        message = message.strip()
        cls.logger.warning(message)


def issue_token(_fqdn, username, password, _verify):
    verify_ca_certificate(_verify)
    port = 9527
    path = "/restda/oauth2/token"
    request_url = "https://{}:{}{}".format(_fqdn, port, path)
    request_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    grant_type = "client_credentials"
    payload = {"grant_type": grant_type}

    ret = requests.post(request_url, data=payload, headers=request_headers, auth=HTTPBasicAuth(username, password),
                        verify=_verify, allow_redirects=False)
    try:
        response = json.loads(ret.text)
    except Exception as err:
        Logger.error("response: {}, error: {}".format(ret.text, err))
        return "", ""
    Logger.info("{} {}".format(ret.request.method, ret.request.url))
    Logger.info("Headers: {}".format(ret.request.headers))
    Logger.info("Body: {}".format(ret.request.body))

    Logger.info("Response: {}".format(json.dumps(response, indent=4)))
    if "token_type" in response and "token_key" in response:
        return response["token_type"], response["token_key"]
    else:
        raise requests.HTTPError(response)


def qurey_brief_info_of_template(_fqdn, _token_type, _token, _verify):
    """
    refer cudo link:
    http://belk.netact.noklab.net/N1X_TRUNK/topic/rest_api/concepts/query_brief_info_template.html?cp=13_15_3_2_0
    """
    verify_ca_certificate(_verify)
    port = 9527
    path = "/restda/api/v1/templates"
    request_url = "https://{}:{}{}".format(_fqdn, port, path)
    request_headers = {"Content-Type": "application/json", "Authorization": "{} {}".format(_token_type, _token)}
    ret = requests.get(request_url, headers=request_headers, verify=_verify, allow_redirects=False)
    Logger.info("{} {}".format(ret.request.method, ret.request.url))
    Logger.info("Headers: {}".format(ret.request.headers))
    response = json.loads(ret.text)
    Logger.info("Response: {}".format(json.dumps(response, indent=4)))


def create_a_plan(_fqdn, _token_type, _token, _verify):
    """
    refer cudo link:
    http://belk.netact.noklab.net/N1X_TRUNK/topic/rest_api/concepts/create_plan.html?cp=13_15_3_3_0
    """
    verify_ca_certificate(_verify)
    port = 9527
    path = "/restda/api/v1/plans"
    request_url = "https://{}:{}{}".format(_fqdn, port, path)
    request_headers = {"Content-Type": "application/json", "Authorization": "{} {}".format(_token_type, _token)}
    payload = {"name": "User1_CreatePlan_001",
               "description": "User1 Create the first plan",
               "templateId": "Predefined_performanceData_v1",
               "argumentList": [
                   {"adaptationId": "nokgnb",
                    "startTime": "2021-01-01T10:00:00",
                    "endTime":"2021-01-02T10:00:00"
                    }
               ]
               }
    ret = requests.post(request_url, data=json.dumps(payload, indent=4), headers=request_headers, verify=_verify,
                        allow_redirects=False)
    Logger.info("{} {}".format(ret.request.method, ret.request.url))
    Logger.info("Headers: {}".format(ret.request.headers))
    Logger.info("Body: {}".format(ret.request.body))
    response = json.loads(ret.text)
    Logger.info("Response: {}".format(json.dumps(response, indent=4)))
    assert response["status"] == "success"


def get_root_ca_certificate():
    """
    Importing NetAct CA certificate to RESTDA client:
    http://belk.netact.noklab.net/N1X_TRUNK/topic/rest_api/concepts/install_roo_ca_to_rest.html?cp=13_15_1_4_0
    ssh dmgr node, execute below command
    #cd  /opt/oss/NSN-sm_conf_cert/bin/
    #./smcert_get_root_cert.sh --serviceName restda

    following above cudo link, you can generate restda_nbi_open_api.pem
    """
    return join(dirname(abspath(__file__)), "restda_nbi_open_api.pem")


def verify_ca_certificate(ca_path):
    if ca_path and not exists(ca_path):
        raise FileNotFoundError(ca_path)


if __name__ == "__main__":
    fqdn = "clab1271lbwas.netact.nsn-rdnet.net"
    root_ca_certificate = get_root_ca_certificate()

    # InsecureRequest for issue token, urllib3 will raise InsecureRequestWarning.
    # issue_token(fqdn, "omc", "omc", False)

    # SecureRequest for issue token
    token_type, token = issue_token(fqdn, "omc", "omc", root_ca_certificate)

    # SecureRequest for query brief info of template
    # qurey_brief_info_of_template(fqdn, token_type, token, root_ca_certificate)

    for i in range(50):
    # SecureRequest for create a plan
        create_a_plan(fqdn, token_type, token, root_ca_certificate)
