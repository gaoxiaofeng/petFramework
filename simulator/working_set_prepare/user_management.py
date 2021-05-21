from selenium.webdriver.common.keys import Keys
import time
from startpage import StartPage
from logger import Logger


class UserManagement(object):
    def __init__(self):
        super(UserManagement, self).__init__()
        self.browser = StartPage()
        self.group_index = None

    def open_user_management(self, url, user='omc', passwd='omc'):
        self.browser.open_chrome()
        self.browser.get(url)
        self.browser.login(user=user, passwd=passwd)
        self.browser.show_applications_all()
        self.browser.open_application("Manages and administers users and user groups.")

    def create_user(self, user='rUser', group='restda_user_group', count=1):
        self._create_user_or_modify_user(user)
        if self.user_create_mode == 'new':
            self._type_basic(user)
            self._type_additional()
            self._type_expiration()
        added_user = self._create_user_into_group(user, group, count)
        if added_user:
            Logger.info("save this created")
            self._click_create()
        else:
            Logger.info("no user be created, bye")
            self.browser.close()

    def _create_user_or_modify_user(self, user):
        items_per_page = self.browser.find_element(
            "/html/body/form/table[1]/tbody/tr[5]/td/table/tfoot/tr/td/div[3]/span/select")
        items_per_page.click()
        for i in range(5):
            items_per_page.send_keys(Keys.ARROW_DOWN)
        items_per_page.click()
        account_exist = False
        for i in range(10000):
            try:
                user_item = self.browser.find_element(
                    "/html/body/form/table[1]/tbody/tr[5]/td/table/tbody/tr[{}]/td[2]".format(i + 1), max_retry=1)
                if user_item.text == user:
                    check_box = self.browser.find_element(
                        "/html/body/form/table[1]/tbody/tr[5]/td/table/tbody/tr[{}]/td[1]/input".format(i + 1),
                        max_retry=1)
                    check_box.click()
                    account_exist = True
                    break
            except Exception as err:
                break

        if account_exist:
            Logger.info('account is exist, expend it.')
            self.user_create_mode = 'modify'
            modify_button = self.browser.find_element("/html/body/form/table[2]/tbody/tr/td[2]/input")
            modify_button.click()
        else:
            Logger.info('acount is not exist, create it.')
            self.user_create_mode = 'new'
            new_button = self.browser.find_element("/html/body/form/table[2]/tbody/tr/td[1]/input")
            new_button.click()

    def _type_basic(self, user):
        Logger.info('basic label typing')
        basic_label = self.browser.find_element(
            "/html/body/form/div/div[2]/table/tbody/tr[1]/td/table/tbody/tr/td[2]/table/tbody/tr/td[2]/table/tbody/tr/td")
        basic_label.click()
        first_name = self.browser.find_element(
            "/html/body/form/div/div[2]/table/tbody/tr[2]/td[1]/table/tbody/tr/td/table/tbody/tr[1]/td[2]/table/tbody/tr/td[2]/input")
        first_name.clear()
        first_name.send_keys(user)
        last_name = self.browser.find_element(
            "/html/body/form/div/div[2]/table/tbody/tr[2]/td[1]/table/tbody/tr/td/table/tbody/tr[2]/td[2]/table/tbody/tr/td[3]/input")
        last_name.clear()
        last_name.send_keys(user)
        email_id = self.browser.find_element(
            "/html/body/form/div/div[2]/table/tbody/tr[2]/td[1]/table/tbody/tr/td/table/tbody/tr[3]/td[2]/input")
        email_id.clear()
        email_id.send_keys("test@nokia-sbell.com")

    def _type_additional(self):
        Logger.info('additional label typing')
        additional_label = self.browser.find_element(
            "/html/body/form/div/div[2]/table/tbody/tr[1]/td/table/tbody/tr/td[4]/table/tbody/tr/td[2]/table/tbody/tr/td")
        additional_label.click()
        employee_id = self.browser.find_element(
            "/html/body/form/div/div[2]/table/tbody/tr[2]/td[2]/table/tbody/tr/td/table/tbody/tr[1]/td[2]/input")
        employee_id.clear()
        employee_id.send_keys('666666')
        mobile_phone = self.browser.find_element(
            "/html/body/form/div/div[2]/table/tbody/tr[2]/td[2]/table/tbody/tr/td/table/tbody/tr[2]/td[2]/input")
        mobile_phone.clear()
        mobile_phone.send_keys('13988888888')
        business_phone = self.browser.find_element(
            "/html/body/form/div/div[2]/table/tbody/tr[2]/td[2]/table/tbody/tr/td/table/tbody/tr[3]/td[2]/input")
        business_phone.clear()
        business_phone.send_keys('028888888')
        fax = self.browser.find_element(
            "/html/body/form/div/div[2]/table/tbody/tr[2]/td[2]/table/tbody/tr/td/table/tbody/tr[4]/td[2]/input")
        fax.clear()
        fax.send_keys("123456")
        address_line_1 = self.browser.find_element(
            "/html/body/form/div/div[2]/table/tbody/tr[2]/td[2]/table/tbody/tr/td/table/tbody/tr[5]/td[2]/input")
        address_line_1.clear()
        address_line_1.send_keys("chengdu")

    def _type_expiration(self):
        Logger.info('expiration label typing')
        expiration = self.browser.find_element(
            "/html/body/form/div/div[2]/table/tbody/tr[1]/td/table/tbody/tr/td[6]/table/tbody/tr/td[2]/table/tbody/tr/td")
        expiration.click()
        never_check_box = self.browser.find_element(
            "/html/body/form/div/div[2]/table/tbody/tr[2]/td[3]/table/tbody/tr/td/table/tbody/tr/td[1]/table/tbody/tr[1]/td/input")
        never_check_box.click()

    def _create_user_into_group(self, user, group, count):
        added_users = []
        exist_users = self._get_exist_user()
        Logger.info('already exist users: {}'.format(exist_users))
        for i in range(count):
            user_name = "{}_{}".format(user, i + 1)
            if user_name in exist_users:
                Logger.info("user: {} is already exists, ignore creating.".format(user_name))
            else:
                Logger.info("creating user: {}".format(user_name))
                self._type_login_profile_details(user_name)
                self._associate_groups_for_account(group)
                self._click_add_button()
                added_users.append(user_name)
        return added_users

    def _type_login_profile_details(self, user):
        login_name = self.browser.find_element(
            "/html/body/form/table[1]/tbody/tr/td[1]/div/div[2]/table[1]/tbody/tr[1]/td[2]/table/tbody/tr/td[2]/input")
        login_name.clear()
        login_name.send_keys(user)
        password = self.browser.find_element(
            "/html/body/form/table[1]/tbody/tr/td[1]/div/div[2]/table[1]/tbody/tr[2]/td[2]/table/tbody/tr/td[2]/input")
        password.clear()
        password.send_keys("Nokia123!")
        confirm_password = self.browser.find_element(
            "/html/body/form/table[1]/tbody/tr/td[1]/div/div[2]/table[1]/tbody/tr[3]/td[2]/table/tbody/tr/td[2]/input")
        confirm_password.clear()
        confirm_password.send_keys("Nokia123!")
        password_never_expires = self.browser.find_element(
            "/html/body/form/table[1]/tbody/tr/td[1]/div/div[2]/table[1]/tbody/tr[4]/td[2]/input")
        password_never_expires.click()

    def _get_exist_user(self):
        users = []
        for i in range(10000):
            try:
                user = self.browser.find_element(
                    "/html/body/form/table[1]/tbody/tr/td[2]/div/div[2]/div/table/tbody/tr[{}]/td[2]".format(i + 1),
                    max_retry=1)
                user_name = user.text
                users.append(user_name)
            except Exception as err:
                break
        try:
            user = self.browser.find_element(
                "/html/body/form/table[1]/tbody/tr/td[2]/div/div[2]/div/table/tbody/tr/td[2]", max_retry=1)
            user_name = user.text
            users.append(user_name)
        except Exception as err:
            pass
        return users

    def _associate_groups_for_account(self, target_group):
        target_group_exist = False
        group_indexes = list(range(1, 10000))
        if self.group_index:
            group_indexes = [self.group_index] + group_indexes
        for i in group_indexes:
            try:
                group = self.browser.find_element(
                    "/html/body/form/table[1]/tbody/tr/td[1]/div/div[2]/div/div[1]/table/tbody/tr[{}]/td[2]".format(i),
                    max_retry=1)
                group_name = group.text
                if group_name == target_group:
                    group_check_box = self.browser.find_element(
                        "/html/body/form/table[1]/tbody/tr/td[1]/div/div[2]/div/div[1]/table/tbody/tr[{}]/td[1]/input".format(
                            i), max_retry=1)
                    group_check_box.click()
                    target_group_exist = True
                    self.group_index = i
                    break
            except Exception as err:
                break
        if not target_group_exist:
            raise Exception("target group {} is not exist, please create it on monitor UI.".format(target_group))

    def _click_add_button(self):
        start_time = time.time()
        add_button = self.browser.find_element(
            "/html/body/form/table[1]/tbody/tr/td[1]/div/div[2]/table[2]/tbody/tr/td[1]/input")
        while 1:
            if time.time() - start_time > 10:
                raise Exception("add button is not enable after selected groups in 10 mins")
            if add_button.is_enabled():
                break
            else:
                time.sleep(1)
        add_button.click()

    def _click_create(self):
        create_button = self.browser.find_element("/html/body/form/table[2]/tbody/tr/td[1]/input")
        if create_button.is_enabled():
            create_button.click()
        else:
            raise Exception("create button is not enable")


if __name__ == '__main__':
    browser = UserManagement()
    browser.open_user_management("https://clab2086lbwas.netact.nsn-rdnet.net/authentication/Login", passwd='omc')
    browser.create_user(user="guy", group='restda_user_group', count=10)
