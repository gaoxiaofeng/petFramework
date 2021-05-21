import os
from os.path import exists, dirname, abspath, isdir, join
from logger import Logger
from pyzabbix import ZabbixAPI
import datetime
import time
import urllib
from urllib.request import build_opener, HTTPCookieProcessor
from urllib.parse import urlencode


class Zabbix(object):
    def __init__(self, url="http://10.91.60.66/zabbix/", outputdir=dirname(abspath(__file__))):
        super(Zabbix, self).__init__()
        self.zabbix_url = url
        self.zabbix_graph_url = "{}/chart2.php".format(self.zabbix_url.rstrip("/"))
        self.zabbix_user = None
        self.zabbix_passwd = None
        self.zabbix_api = None
        self._downloader = None
        self.outputdir = join(outputdir, 'graphs')
        self.resource_usage_warning_file = join(self.outputdir, "resource_usage_warning.csv")

    def download_screen_graphs(self, screenid='238', starttime="2019-11-28 10:00:00", endtime="2019-12-02 08:00:00"):
        self._login()
        self._create_graph_dir()
        # self._verify_resource_usage(screenid, starttime, endtime)
        self._download_screen_graphs(screenid, starttime, endtime)
        self._logout()

    def _login(self, user="Admin", password="zabbix"):
        Logger.info("access: {}".format(self.zabbix_url))
        self.zabbix_user = user
        self.zabbix_passwd = password
        self.zabbix_api = ZabbixAPI(server=self.zabbix_url)
        self.zabbix_api.login(self.zabbix_user, self.zabbix_passwd)
        version = self.zabbix_api.api_version()
        Logger.info("Zabbix Version: {}".format(version))

    def _logout(self):
        if self.zabbix_api:
            self.zabbix_api.user.logout()

    def _download_screen_graphs(self, screenid, starttime, endtime):
        _starttime = datetime.datetime.strptime(starttime, "%Y-%m-%d %H:%M:%S")
        _endtime = datetime.datetime.strptime(endtime, "%Y-%m-%d %H:%M:%S")
        start_timestamp = int(time.mktime(_starttime.timetuple()))
        end_timestamp = int(time.mktime(_endtime.timetuple()))
        period = end_timestamp - start_timestamp
        stime = _starttime.strftime("%Y%m%d%H%M%S")
        screen = self.zabbix_api.do_request('screen.get',
                                            params={"output": "extend",
                                                    "selectScreenItems": "extend",
                                                    "selectUsers": "extend",
                                                    "selectUserGroups": "extend",
                                                    "screenids": screenid})
        screen_graphs = screen["result"][0]["screenitems"]
        for screen_graph in screen_graphs:
            graphid = screen_graph["resourceid"]
            height = screen_graph["height"]
            width = screen_graph["width"]
            graph = self.zabbix_api.do_request("graph.get", params={"output": "extend", "graphids": graphid})
            graph_name = graph["result"][0]["name"]
            host = self.zabbix_api.do_request("host.get", params={"output": "extend", "graphids": graphid})
            host_name = host["result"][0]["host"]
            Logger.debug(
                "zabbix graph name:{}, graphid:{}, host:{}, size: {}*{}".format(graph_name, graphid, host_name, height,
                                                                                width))
            graph_args = urlencode({
                "graphid": graphid,
                "screenid": screenid,
                "stime": stime,
                "period": period,
                "width": width,
                "height": height
            })
            graph_file_name = "{host_name}_{graph_name}.png".format(host_name=host_name,
                                                                    graph_name=self._name_replace(graph_name))
            graph_file_path = join(self.outputdir, graph_file_name)
            image = self.downloader.open(self.zabbix_graph_url, graph_args.encode('utf-8')).read()
            with open(graph_file_path, 'wb') as f:
                f.write(image)
            Logger.info("download Zabbix graph: {}".format(graph_file_name))

    @property
    def downloader(self):
        if not self._downloader:
            login_data = urlencode({
                "name": self.zabbix_user,
                "password": self.zabbix_passwd,
                "autologin": 1,
                "enter": "Sign in"})
            self._downloader = build_opener(HTTPCookieProcessor())
            response = self._downloader.open(self.zabbix_url, login_data.encode('utf-8'))
            Logger.info("Login Zabbix via urllib, response: {}".format(response))
        return self._downloader

    @staticmethod
    def _name_replace(name):
        return name.replace(" ", "_").replace("/", "_").replace("%", "")

    def _create_graph_dir(self):
        if not (exists(self.outputdir) and isdir(self.outputdir)):
            try:
                os.mkdir(self.outputdir)
            except Exception as err:
                Logger.error("create graph directory failed: {}".format(self.outputdir))
                Logger.error(err)
                exit(1)

    def _verify_resource_usage(self, screenid, starttime, endtime,
                               lab_timezone=2):
        errors = ["host,errors"]
        _starttime = datetime.datetime.strptime(starttime, "%Y-%m-%d %H:%M:%S") + datetime.timedelta(
            hours=self.local_timezone - lab_timezone)
        _endtime = datetime.datetime.strptime(endtime, "%Y-%m-%d %H:%M:%S") + datetime.timedelta(
            hours=self.local_timezone - lab_timezone)
        start_timestamp = int(time.mktime(_starttime.timetuple()))
        end_timestamp = int(time.mktime(_endtime.timetuple()))
        screen = self.zabbix_api.do_request('screen.get',
                                            params={"output": "extend",
                                                    "selectScreenItems": "extend",
                                                    "selectUsers": "extend",
                                                    "selectUserGroups": "extend",
                                                    "screenids": screenid})
        screen_graphs = screen["result"][0]["screenitems"]
        for screen_graph in screen_graphs:
            graph_id = screen_graph["resourceid"]
            graph_item_ids = self._get_graphitem(graph_id)
            graph_item_map = self._get_item(graph_item_ids)
            graph_name = self._get_graph_name(graph_id)
            hostid, hostname = self._get_host_name(graph_id)
            for item_id in graph_item_map:
                item_key = graph_item_map[item_id]

                error = self._verify_items_value(hostid, hostname, item_id, graph_name, item_key, start_timestamp,
                                                 end_timestamp)
                errors += error
        self._save_resource_usage(errors)

    @property
    def local_timezone(self):
        return 0 - time.timezone / 3600

    def _save_resource_usage(self, errors):
        with open(self.resource_usage_warning_file, "wb") as f:
            f.write("\n".join(errors).encode('utf-8'))

    def _get_cpu_usage_average(self, hostid, item_id, start_timestamp, end_timestamp):
        history_data = self._get_history(hostid, item_id, start_timestamp, end_timestamp)
        maximum, minimum, average = self._aggregate_history(history_data)
        cpu_usage_average = 100 - average
        cpu_usage_maximum = 100 - minimum
        cpu_usage_minimum = 100 - maximum
        Logger.debug("result: {}[max], {}[min], {}[average]".format(cpu_usage_maximum, cpu_usage_minimum, cpu_usage_average))
        return cpu_usage_average

    def _get_mem_usage_average(self, hostid, item_id, start_timestamp, end_timestamp):
        history_data = self._get_history(hostid, item_id, start_timestamp, end_timestamp)
        maximum, minimum, average = self._aggregate_history(history_data)
        mem_usage_average = 100 - average
        mem_usage_maximum = 100 - minimum
        mem_usage_minimum = 100 - maximum
        Logger.debug("result: {}[max], {}[min], {}[average]".format(mem_usage_maximum, mem_usage_minimum, mem_usage_average))
        return mem_usage_average

    def _get_swap_in_out_average(self, hostid, item_id, start_timestamp, end_timestamp):
        history_data = self._get_history(hostid, item_id, start_timestamp, end_timestamp)
        maximum, minimum, average = self._aggregate_history(history_data)
        Logger.debug("result: {}[max], {}[min], {}[average]".format(maximum, minimum, average))
        return average

    def _verify_items_value(self, hostid, hostname, item_id, graph_name, item_key, start_timestamp, end_timestamp):
        errors = []
        if item_key == "system.cpu.util[,idle]":
            cpu_usage_average = self._get_cpu_usage_average(hostid, item_id, start_timestamp, end_timestamp)
            if cpu_usage_average is None or cpu_usage_average and cpu_usage_average > 80:
                Logger.warning("host: {}, cpu usage average > 80%".format(hostname))
                errors.append("{},cpu usage average > 80%".format(hostname))
        elif item_key in ["system.cpu.util[,nice]",
                          "system.cpu.util[,softirq]",
                          "system.cpu.util[,user]",
                          "system.cpu.util[,system]",
                          "system.cpu.util[,steal]",
                          "system.cpu.util[,interrupt]",
                          "system.cpu.util[,iowait]",
                          "system.swap.size[,total]",
                          "system.swap.size[,free]"]:
            pass
        elif item_key == "vm.memory.size[pavailable]":
            mem_usage_average = self._get_mem_usage_average(hostid, item_id, start_timestamp, end_timestamp)
            if mem_usage_average is None or mem_usage_average and mem_usage_average > 80:
                Logger.warning("host: {}, memory usage average:{} > 80%".format(hostname, mem_usage_average))
                errors.append("{},memory usage average:{} > 80%".format(hostname, mem_usage_average))
            else:
                Logger.info("host: {}, memory usage average: {}".format(hostname, mem_usage_average))
        elif item_key == "system.swap.in[,pages]":
            average = self._get_swap_in_out_average(hostid, item_id, start_timestamp, end_timestamp)
            if average is None or average and average > 1:
                Logger.warning("host: {}, swap in: {} > 1".format(hostname, average))
                errors.append("{},swap in: {} > 1".format(hostname, average))
            else:
                Logger.info("host: {}, swap in: {}".format(hostname, average))

        elif item_key == "system.swap.out[,pages]":
            average = self._get_swap_in_out_average(hostid, item_id, start_timestamp, end_timestamp)
            if average is None or average and average > 1:
                Logger.warning("host: {}, swap out: {} > 1".format(hostname, average))
                errors.append("{},swap out: {} > 1".format(hostname, average))
            else:
                Logger.info("host: {}, swap out: {}".format(hostname, average))

        else:
            Logger.warning("unkown host: {}, graph_name: {}, item_name: {}".format(hostname, graph_name, item_key))
        return errors

    def _get_graphitem(self, graphid):
        item_ids = []
        graphitems = self.zabbix_api.do_request("graphitem.get", params={"output": "extend", "graphids": graphid})
        for graphitem in graphitems["result"]:
            item_ids.append(graphitem["itemid"])
        return item_ids

    def _get_item(self, item_id):
        item_map = dict()
        items = self.zabbix_api.do_request("item.get", params={"output": "extend", "itemids": item_id})
        for item in items["result"]:
            description = item["description"]
            key = item["key_"]
            item_id = item["itemid"]
            name = item["name"]
            Logger.debug("item key: {}, item name: {}, item description: {}".format(key, name, description))
            item_map.update({item_id: key})
        return item_map

    def _get_graph_name(self, graphid):
        graph = self.zabbix_api.do_request("graph.get", params={"output": "extend", "graphids": graphid})
        graph_name = graph["result"][0]["name"]
        return graph_name

    def _get_host_name(self, graphid):
        host = self.zabbix_api.do_request("host.get", params={"output": "extend", "graphids": graphid})
        hostname = host["result"][0]["host"]
        hostid = host["result"][0]["hostid"]
        return hostid, hostname

    def _get_history(self, hostid, itemid, start_timestamp, end_timestamp, debug=False):
        history = self.zabbix_api.do_request("history.get", params={"hostids": hostid, "itemids": itemid,
                                                                    "output": "extend", "history": 0,
                                                                    "time_from": start_timestamp,
                                                                    "time_till": end_timestamp})
        if debug:
            Logger.debug(str(
                {"hostids": hostid, "itemids": itemid, "output": "extend", "history": 0,
                 "time_from": start_timestamp, "time_till": end_timestamp}))
            Logger.debug(str(history))
        return history

    @staticmethod
    def _aggregate_history(history_datas):
        values = []
        for data in history_datas["result"]:
            values.append(float(data["value"]))
        if values:
            return max(values), min(values), sum(values) / len(values)
        else:
            return None, None, None
