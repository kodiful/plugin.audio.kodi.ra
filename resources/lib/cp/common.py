# -*- coding: utf-8 -*-

from ..common import *

import os


class Params:
    # ファイルパス
    DATA_PATH = ''
    # ファイル
    STATION_FILE = ''
    SETTINGS_FILE = ''
    # URL
    STATION_URL = ''
    SETTINGS_URL = ''


class Common(Params):

    def __init__(self, renew=False):
        return

    def setup(self, renew=False):
        return

    def getStationData(self):
        if not os.path.isfile(self.STATION_FILE):
            self.setup()
        return read_json(self.STATION_FILE)

    def getSettingsData(self):
        if not os.path.isfile(self.SETTINGS_FILE):
            self.setup()
        return read_file(self.SETTINGS_FILE)

    def getProgramFile(self):
        return

    def getProgramData(self, renew=False):
        return
