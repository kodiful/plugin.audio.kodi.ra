# -*- coding: utf-8 -*-

from ..const import Const
from ..common import *

import os


class Params:
    # 放送局情報
    STATION_FILE = ''
    # 設定ダイアログ
    SETTINGS_FILE = ''


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

    def getProgramData(self, renew=False):
        return [{'id': s['id'], 'progs': [{'title': s.get('onair',Const.STR(30059))}]} for s in self.getStationData()]
