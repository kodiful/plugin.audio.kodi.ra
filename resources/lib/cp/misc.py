# -*- coding: utf-8 -*-

from ..const import Const
from ..common import *
from ..xmltodict import parse

import os, sys
import urllib
import xml.dom.minidom
import re
import json
import xbmc, xbmcgui, xbmcplugin, xbmcaddon


class Params:
    # ファイルパス
    DATA_PATH = os.path.join(Const.DATA_PATH, 'misc')
    if not os.path.isdir(DATA_PATH): os.makedirs(DATA_PATH)
    # ファイル
    STATION_FILE = os.path.join(DATA_PATH, 'station.json')
    SETTINGS_FILE = os.path.join(DATA_PATH, 'settings.xml')


class Misc(Params):

    def __init__(self, renew=False):
        self.id = 'misc'
        # 放送局データをファイルから読み込む
        self.read()
        # 放送局データと設定データを初期化
        self.getStationFile(renew)

    def read(self):
        self.ch = read_json(Const.CHANNELS_FILE) or []

    def write(self):
        write_json(Const.CHANNELS_FILE, self.ch)

    def getStationFile(self, renew=False):
        # キャッシュがあれば何もしない
        if renew == False and os.path.isfile(self.STATION_FILE) and os.path.isfile(self.SETTINGS_FILE):
            return
        # 放送局データ
        buf = []
        for id, ch in enumerate(self.ch):
            buf.append({
                'id': 'misc_%03d' % id,
                'name': ch['name'],
                'logo_large': '',
                'url': ch['stream']
            })
        # 放送局データを書き込む
        write_json(self.STATION_FILE, buf)
        # 設定データ
        buf = []
        for id, ch in enumerate(self.ch):
            buf.append(
                '    <setting label="{name}" type="bool" id="misc_{id:03d}" default="true" enable="eq({offset},2)" visible="true"/>'
                .format(name=ch['name'], id=id, offset=-1-id))
        # 設定データを書き込む
        write_file(self.SETTINGS_FILE, '\n'.join(buf))

    def getStationData(self):
        return read_json(self.STATION_FILE)

    def getSettingsData(self):
        return read_file(self.SETTINGS_FILE)

    def getProgramFile(self):
        return

    def getProgramData(self, renew=False):
        return [{'id': s['id'], 'progs': [{'onair': s.get('onair','')}]} for s in self.getStationData()]

    def edit(self, id):
        ch = self.ch[int(id)]
        Const.SET('id',str(id))
        Const.SET('name',ch['name'])
        Const.SET('stream',ch['stream'])
        xbmc.executebuiltin('Addon.OpenSettings(%s)' % Const.ADDON_ID)
        xbmc.executebuiltin('SetFocus(103)') # select 4th category
        xbmc.executebuiltin('SetFocus(201)') # select 2nd control

    def edited(self, id, name, stream):
        if name and stream:
            if id == '':
                self.ch.append({'name':name, 'stream':stream})
            elif int(id) < len(self.ch):
                self.ch[int(id)]['name'] = name
                self.ch[int(id)]['stream'] = stream
            else:
                return
            # 追加/編集した設定を書き込む
            self.write()
            # 変更を反映する
            self.getStationFile(renew=True)
            xbmc.executebuiltin('RunPlugin(%s?action=reset)' % (sys.argv[0]))

    def delete(self, id):
        if int(id) < len(self.ch):
            # id番目の要素を削除
            self.ch.pop(int(id))
            # 削除した設定を書き込む
            self.write()
            # 変更を反映する
            self.getStationFile(renew=True)
            xbmc.executebuiltin('RunPlugin(%s?action=reset)' % (sys.argv[0]))
