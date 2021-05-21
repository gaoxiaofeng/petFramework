from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
from logger import Logger
# import traceback


class StartPage(object):
    def __init__(self):
        super(StartPage, self).__init__()
        self.driver = None

    def open_chrome(self):
        option = Options()
        option.add_argument("--ignore-certificate-errors")
        option.add_argument("--allow-running-insecure-content")
        self.driver = webdriver.Chrome(chrome_options=option)
        self.driver.implicitly_wait(30)
        self.driver.maximize_window()

    def close(self):
        if self.driver:
            self.driver.close()

    def get(self, url):
        self.driver.get(url)
        time.sleep(3)

    def login(self, user='omc', passwd='omc'):
        user_elem = self.driver.find_element_by_xpath('/html/body/div[3]/div[2]/div[2]/div[2]/form/div[1]/div[1]/input')
        user_elem.clear()
        user_elem.send_keys(user)
        time.sleep(0.5)
        passwd_elem = self.driver.find_element_by_xpath(
            '/html/body/div[3]/div[2]/div[2]/div[2]/form/div[1]/div[2]/input')
        passwd_elem.clear()
        passwd_elem.send_keys(passwd)
        login_button = self.driver.find_element_by_xpath('/html/body/div[3]/div[2]/div[2]/div[2]/form/div[2]/input')
        login_button.click()
        accept_button = self.driver.find_element_by_xpath(
            '/html/body/div[2]/div[2]/div[2]/div[2]/div[4]/div[2]/form/div/input')
        accept_button.click()

    def show_applications_all(self):
        link = self.driver.find_element_by_xpath('/html/body/div[1]/div[1]/div/div[2]/div[3]/ul/li/a')
        link.click()
        button = self.driver.find_element_by_xpath('/html/body/div[8]/ul/li/a')
        button.click()

    def open_application(self, app_description):
        for i in range(1, 100):
            try:
                app = self.driver.find_element_by_xpath('/html/body/div[1]/div[2]/div/a[{}]'.format(i))
                app_name = app.get_attribute("appname")
                if app_name == app_description:
                    app.click()
                    break
            except Exception as err:
                Logger.error("do not find this app: {}".format(app_description))
                Logger.error("error: {}".format(err))
                exit(1)
        self.driver.switch_to.window(self.driver.window_handles[1])

    def find_element(self, xpath, max_retry=1):
        for i in range(1, max_retry + 1):
            try:
                element = self.driver.find_element_by_xpath(xpath)
            except Exception as err:
                Logger.error("find element by {} failed in {} times, reason: {}".format(xpath, i, err))
                if i == max_retry:
                    raise Exception(err)
                else:
                    time.sleep(5)
            else:
                Logger.debug("found element: {}".format(xpath))
                return element
