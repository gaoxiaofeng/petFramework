from Handler import *


class Client(object):
    def __init__(self):
        super(Client, self).__init__()

    @staticmethod
    def handle(**kwargs):
        # set home folder
        h1 = InitEnv()
        h2 = StartMaster()
        h3 = AttachMaster()
        h1.successor = h2
        h2.successor = h3
        h1.handle(**kwargs)
