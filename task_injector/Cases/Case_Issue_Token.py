from Cases._RestdaCase import _RestdaCase
from Util.platform import *


class Case(_RestdaCase):
    def __init__(self):
        super(Case, self).__init__()
        self.ThinkTime = 30

    def action(self):
        # user_id = (self.Counter % 900) + 101
        # user_name = 'pet_{}'.format(user_id)
        # password = 'Nokia123!'
        user_name = "omc"
        password = "omc"
        RestdaAPI().issue_token(user_name, self.CacheFile, password=password)
