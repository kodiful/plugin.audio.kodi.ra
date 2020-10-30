# -*- coding: utf-8 -*-

from ..const import Const
from ..common import *
from ..xmltodict import parse

import os
import xml.dom.minidom
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
    STATION_URL   = 'http://kodiful.com/KodiRa/downloads/jcba/station.xml'
    SETTINGS_URL  = 'http://kodiful.com/KodiRa/downloads/jcba/settings.xml'


class Jcba(Params):

    def __init__(self, renew=False):
        self.id = 'jcba'
        # 放送局データと設定データを初期化
        self.getStationFile(renew)

    def getStationFile(self, renew=False):
        # キャッシュがあれば何もしない
        if renew == False and os.path.isfile(self.STATION_FILE) and os.path.isfile(self.SETTINGS_FILE):
            return
        # 放送局データをウェブから読み込む
        data = urlread(self.STATION_URL)
        # データ変換
        dom = convert(parse('<stations>%s</stations>' % data))
        station = dom['stations'].get('station',[]) if dom['stations'] else []
        station = station if isinstance(station,list) else [station]
        # 放送局データ
        buf = []
        for s in station:
            buf.append({
                'id': s['id'],
                'name': s['name'],
                'logo_large': s['logo_large'],
                'url': s['url'],
                'onair': s['onair']
            })
        # 放送局データを書き込む
        write_json(self.STATION_FILE, buf)
        # 設定データをウェブから読み込む
        data = urlread(self.SETTINGS_URL)
        # 設定データを書き込む
        write_file(self.SETTINGS_FILE, data)

    def getStationData(self):
        return read_json(self.STATION_FILE)

    def getSettingsData(self):
        return read_file(self.SETTINGS_FILE)

    def getProgramFile(self):
        return

    def getProgramData(self, renew=False):
        return [{'id': s['id'], 'progs': [{'onair': s.get('onair','')}]} for s in self.getStationData()]
