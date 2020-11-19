# -*- coding: utf-8 -*-

from ..const import Const
from ..common import *

import os


class Params:
    # 放送局データ
    STATION_FILE = os.path.join(Const.TEMPLATE_PATH, 'jcba', 'station.json')
    # 設定ダイアログ
    SETTINGS_FILE = os.path.join(Const.TEMPLATE_PATH, 'jcba', 'settings.xml')


class Jcba(Params):

    def __init__(self, renew=False):
        return

    def setup(self, renew=False):
        # 放送局データを取得、設定ダイアログを書き出す
        return

    def getStationData(self):
        # 放送局データを読み込む
        if not os.path.isfile(self.STATION_FILE):
            self.setup()
        return read_json(self.STATION_FILE)

    def getSettingsData(self):
        # 設定ダイアログを読み込む
        if not os.path.isfile(self.SETTINGS_FILE):
            self.setup()
        return read_file(self.SETTINGS_FILE)

    def getProgramData(self, renew=False):
        # 最新の番組データを取得、なければ放送局データから生成する
        return [{'id': s['id'], 'progs': [{'title': s.get('onair') or Const.STR(30059)}]} for s in self.getStationData()]
