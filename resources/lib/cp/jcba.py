# -*- coding: utf-8 -*-

from common import Common

from ..const import Const
from ..common import *
from ..xmltodict import parse

import os
import re
import xbmc, xbmcgui, xbmcplugin, xbmcaddon


class Params:
    # ファイルパス
    DATA_PATH = os.path.join(Const.DATA_PATH, 'jcba')
    if not os.path.isdir(DATA_PATH): os.makedirs(DATA_PATH)
    # ファイル
    STATION_FILE = os.path.join(DATA_PATH, 'station.json')
    SETTINGS_FILE = os.path.join(DATA_PATH, 'settings.xml')
    # URL
    STATION_URL   = 'http://kodiful.com/KodiRa/jcba/station.json'
    SETTINGS_URL  = 'http://kodiful.com/KodiRa/jcba/settings.xml'


class Jcba(Params, Common):

    def __init__(self, renew=False):
        self.id = 'jcba'
        # 放送局データと設定データを初期化
        self.setup(renew)

    def setup(self, renew=False):
        # キャッシュがあれば何もしない
        if renew == False and os.path.isfile(self.STATION_FILE) and os.path.isfile(self.SETTINGS_FILE):
            return
        # 放送局データをウェブから読み込む
        data = urlread(self.STATION_URL)
        if data:
            # 放送局データを書き込む
            write_file(self.STATION_FILE, data)
            # 設定データをウェブから読み込む
            data = urlread(self.SETTINGS_URL)
            # 設定データを書き込む
            write_file(self.SETTINGS_FILE, data)
        else:
            # 放送局データを書き込む
            write_json(self.STATION_FILE, [])
            # 設定データを書き込む
            write_file(self.SETTINGS_FILE, '')
