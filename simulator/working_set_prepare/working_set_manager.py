import time
from startpage import StartPage


class WorkingSetManager(object):
    def __init__(self):
        super(WorkingSetManager, self).__init__()
        self.browser = StartPage()
        self.driver = self.browser.driver

    def open_working_set_manager(self, url, user='omc', passwd='omc'):
        self.browser.open_chrome()
        self.browser.get(url)
        self.browser.login(user=user, passwd=passwd)
        self.browser.show_applications_all()
        self.browser.open_application("Creates and manages working sets.")

    def create_working_set(self, name='', rule=''):
        create_button = self.browser.find_element("/html/body/div[1]/div/div[3]/div/div/div[2]/div[1]/working-set-list/div/div/div[1]/button[3]")
        create_button.click()
        cm_query = self.browser.find_element("/html/body/div[1]/div/div[3]/div/div/div[2]/div[1]/div/ul/li[4]/a")
        cm_query.click()
        working_set_rule_elem = self.browser.find_element("/html/body/div[1]/div/div[3]/div/div/div[2]/div[1]/div/div/div/div/div/textarea")
        working_set_rule_elem.send_keys(rule)
        self._wait_syntax_validate()
        working_set_name_elem = self.browser.find_element("/html/body/div[1]/div/div[3]/div/div/div[2]/div[2]/save-wset/div/div[1]/div[4]/input")
        working_set_name_elem.send_keys(name)
        self._wait_save_enable()
        save_button = self.browser.find_element("/html/body/div[1]/div/div[3]/div/div/div[2]/div[2]/save-wset/div/div[4]/button")
        save_button.click()
        self._wait_saved()
        back_button = self.browser.find_element("/html/body/div[1]/div/div[3]/div/div/div[1]/div[1]/h1/button")
        back_button.click()

    def _wait_syntax_validate(self):
        while 1:
            output = self.browser.find_element("/html/body/div[1]/div/div[3]/div/div/div[2]/div[1]/div/div/div/div/div/div/div[2]/span[2]")
            if output.text == "The provided MO Path has a valid syntax.":
                break
            time.sleep(2)

    def _wait_save_enable(self):
        while 1:
            back_button = self.browser.find_element("/html/body/div[1]/div/div[3]/div/div/div[2]/div[2]/save-wset/div/div[4]/button")
            if back_button.is_enabled():
                break
            time.sleep(2)

    def _wait_saved(self):
        while 1:
            output = self.browser.find_element("/html/body/div[1]/div/div[2]/alert-create-working-set/div/div")
            if output.text == "Dynamic Working Set has been successfully created.":
                break
            time.sleep(2)


if __name__ == '__main__':
    working_sets_n19 = [
        ["2G", "/PLMN/BSC"],
        ["3G", "/PLMN/RNC"],
        ["4G", "/PLMN/MRBTS[(dn() like '%-20%') or (dn() like '%-3%') or (dn() like '%-56%')]"],
        ["5G", "/PLMN/MRBTS[(dn() like '%-56%')]"],
        ["4G-large", "/PLMN/MRBTS[(dn() like '%restda%')]"],
        ["CSCF", "PLMN/CSCFLCC/CSCF"],
        ["NAPET", "/PLMN/MRBTS[not (dn() like '%restda%')]"],
    ]

    working_sets_n20_ran_core = [
        ["GSM", "/PLMN/BSC"],
        ["WCDMA", "/PLMN/RNC"],
        ["SBTS", "/PLMN/MRBTS[(dn() like '%-401%') or (dn() like '%-402%') or  (dn() like '%-403000%')]"],
        ["HSS_VNF", "PLMN/IMSNFM/HSS"],
        ["CSCF", "PLMN/CSCFLCC/CSCF"],
        ["MSS", "PLMN/MSC"],
        ["SBTS_CM", "/PLMN/MRBTS[(dn() like '%-403%' ) and not(dn() like '%403000%') or (dn() like '%-404%') or  (dn() like '%-405000%') ]"],
        ["5G", "/PLMN/MRBTS[(dn() like '%-500%' )  or (dn() like '%-501%' ) or (dn() like '%-502000%' )]"]
    ]
    browser = WorkingSetManager()
    browser.open_working_set_manager("https://clab045lbwas.netact.nsn-rdnet.net/", passwd='omc')
    for working_set in working_sets_n20_ran_core:
        browser.create_working_set(name='{}'.format(working_set[0]), rule=working_set[1])
