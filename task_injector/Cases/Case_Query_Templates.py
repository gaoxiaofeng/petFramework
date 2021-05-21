from Cases._RestdaCase import _RestdaCase
from Util.platform import *


class Case(_RestdaCase):
    def __init__(self):
        super(Case, self).__init__()
        self.ThinkTime = 30

    def action(self):
        token = RestdaAPI().read_token(self.CacheFile)
        RestdaAPI().qurey_templates(token)
