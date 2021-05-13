# -*- coding: utf-8 -*-

from resources.lib.cp.jcba import Jcba

from resources.lib.const import Const
from resources.lib.common import read_json
from resources.lib.common import write_json
from resources.lib.common import write_file

import os
import sys

import xbmc

from hashlib import md5
from datetime import datetime, timedelta


class Params:
    # ファイルパス
    DATA_PATH = os.path.join(Const.DATA_PATH, 'simulradio')
    if not os.path.isdir(DATA_PATH):
        os.makedirs(DATA_PATH)
    # ファイル
    STATION_FILE = os.path.join(Const.TEMPLATE_PATH, 'cp', 'community', 'station_sr.json') # 放送局データ

    STN = 'simu_'


class Simulradio(Params, Jcba):

    def __init__(self, renew=False):
        return

    def setup(self, renew=False):
        # 放送局データを取得、設定ダイアログを書き出す
        return

    def getProgramData(self, renew=False):
        # jcba.pyから移設
        # 最新の番組データを取得、なければ放送局データから生成する
        results = [{'id': s['id'], 'progs': [{'title': s.get('onair') or Const.STR(30059)}]} for s in self.getStationData()]
        # デフォルトは更新なし
        nextupdate = '9' * 14
        return results, nextupdate
