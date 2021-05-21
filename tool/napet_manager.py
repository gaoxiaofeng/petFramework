from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import time
import logging
from os.path import join, dirname, abspath
from getpass import getpass


class Logger(object):
    logger = logging.getLogger("Logger")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s: %(message)s')
    # handler = logging.FileHandler(join(dirname(abspath(__file__)), 'napet_manager.log'))
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    @classmethod
    def info(cls, message):
        message = message.strip()
        cls.logger.info(message)
        print(message)

    @classmethod
    def error(cls, message):
        message = message.strip()
        cls.logger.error(message)

    @classmethod
    def debug(cls, message):
        message = message.strip()
        cls.logger.debug(message)

    @classmethod
    def warning(cls, message):
        message = message.strip()
        cls.logger.warning(message)


class browser(object):
    def __init__(self):
        super(browser, self).__init__()

    def open_chrome(self):
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(10)

    def get(self, url):
        self.driver.get(url)

    def login(self, user='omc', passwd='omc'):
        user_elem = self.driver.find_element_by_id("inputUsername")
        passwd_elem = self.driver.find_element_by_id("inputPassword")
        user_elem.clear()
        user_elem.send_keys(user)
        passwd_elem.clear()
        passwd_elem.send_keys(passwd)
        login_elem = self.driver.find_element_by_xpath("/html/body/div[2]/form/div[3]/div/button")
        login_elem.click()

    def set_display_all(self):
        set_elem = self.driver.find_element_by_xpath(
            "/html/body/div[2]/div/div[2]/div[2]/div/table[1]/tbody/tr/td[2]/select")
        set_elem.click()
        set_elem.send_keys(Keys.ARROW_DOWN, Keys.ARROW_DOWN, Keys.ARROW_DOWN, Keys.ARROW_DOWN)
        set_elem.click()
        time.sleep(10)

    def selected_all_machines(self, filter_ip_list = [], selected_ip_list=[]):
        if filter_ip_list and selected_ip_list:
            Logger.error("choose one of filter ip and selected ip.")
            exit(1)
        all_ips = []
        selected_ips = []
        for i in range(1, 1000):
            try:
                machine_ip_elem = self.driver.find_element_by_xpath(
                    "/html/body/div[2]/div/div[2]/div[2]/div/table[2]/tbody/tr[{}]/td[2]".format(i))
                all_ips.append(machine_ip_elem.text)
                if selected_ip_list and machine_ip_elem.text in selected_ip_list:
                    machine_ip_elem.click()
                    selected_ips.append(machine_ip_elem.text)
                elif filter_ip_list and machine_ip_elem.text not in filter_ip_list:
                    machine_ip_elem.click()
                    selected_ips.append(machine_ip_elem.text)
                elif not selected_ip_list and not filter_ip_list:
                    machine_ip_elem.click()
                    selected_ips.append(machine_ip_elem.text)
            except Exception as err:
                break
        Logger.info("all simuhell count: {}".format(len(all_ips)))
        Logger.info(','.join(all_ips))
        Logger.info("selected simuhell count: {}".format(len(selected_ips)))
        Logger.info(','.join(selected_ips))

    def stop(self):
        stop_button = self.driver.find_element_by_xpath("/html/body/div[2]/div/div[1]/button[2]")
        stop_button.click()

    def start(self):
        stop_button = self.driver.find_element_by_xpath("/html/body/div[2]/div/div[1]/button[1]")
        stop_button.click()

    def close(self):
        self.driver.close()

    def extend(self):
        button = self.driver.find_element_by_xpath("/html/body/div[2]/div/div[1]/button[6]")
        assert button.text == "Extend loan period"
        button.click()

filter_ips = ""
filter_ip_list = filter_ips.split(",")
filter_ip_list = list(map(lambda ip: ip.strip(), filter_ip_list))

selected_ips = ""
selected_ip_list = selected_ips.split(",")
selected_ip_list = list(map(lambda ip: ip.strip(), selected_ip_list))

# user = raw_input('user:')
# passwd = getpass(prompt='password:')
# passwd = raw_input('passwd:')
user = 'jargao'
passwd = 'Newmed!@s0beyp'
b = browser()
b.open_chrome()
b.get("https://nsa-napet.netact.nsn-rdnet.net/simuhell")
b.login(user=user, passwd=passwd)
b.set_display_all()
b.selected_all_machines(filter_ip_list=[], selected_ip_list=[])
# b.extend()
time.sleep(300)
b.close()
