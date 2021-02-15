# -*- coding: utf-8 -*-

from resources.lib.const import *
from resources.lib.common import *

import os


class Params:
    # 放送局データ
    STATION_FILE = os.path.join(Const.TEMPLATE_PATH, 'cp', 'jcba', 'station.json')
    # 設定ダイアログ
    SETTINGS_FILE = os.path.join(Const.TEMPLATE_PATH, 'cp', 'jcba', 'settings.xml')


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
        results = [{'id': s['id'], 'progs': [{'title': s.get('onair') or Const.STR(30059)}]} for s in self.getStationData()]
        # デフォルトは更新なし
        nextupdate = '9'*14
        return results, nextupdate

    def getNextUpdate(self, qbuf):
        # 現在時刻
        now = timestamp()
        # 開始/終了時刻が定義された番組を抽出
        p = filter(lambda x:x['ft'] and x['to'], qbuf)
        # 終了済みの番組は現在時刻を、それ以外は開始時刻を抽出
        p = map(lambda x:now if x['to']<now else x['ft'], p)
        # 現在時刻以降の時刻を抽出
        p = filter(lambda t: t>=now, p)
        # 直近の時刻を抽出
        return min(p) if p else now
