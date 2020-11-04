# -*- coding: utf-8 -*-

from common import Common

from ..const import Const
from ..common import *
from ..xmltodict import parse

import os, sys
import urllib
import xml.dom.minidom
import re
import json
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

from hashlib import md5


class Params:
    # ファイルパス
    DATA_PATH = os.path.join(Const.DATA_PATH, 'misc')
    if not os.path.isdir(DATA_PATH): os.makedirs(DATA_PATH)
    # ファイル
    STATION_FILE = os.path.join(DATA_PATH, 'station.json')
    SETTINGS_FILE = os.path.join(DATA_PATH, 'settings.xml')


class Misc(Params, Common):

    def __init__(self, renew=False):
        self.id = 'misc'
        # 放送局データをファイルから読み込む
        self.read()
        # 放送局データと設定データを初期化
        self.setup(renew)

    def read(self):
        self.ch = read_json(Const.CHANNELS_FILE) or []

    def write(self):
        write_json(Const.CHANNELS_FILE, self.ch)

    def setup(self, renew=False):
        # キャッシュがあれば何もしない
        if renew == False and os.path.isfile(self.STATION_FILE) and os.path.isfile(self.SETTINGS_FILE):
            return
        # 放送局データ
        buf = []
        for ch in self.ch:
            ch['id'] = 'misc_%s' % md5(ch['stream']).hexdigest()
            buf.append({
                'id': ch['id'],
                'name': ch['name'],
                'logo_large': '',
                'url': ch['stream'],
                'onair': ''
            })
        # 放送局データを書き込む
        write_json(self.STATION_FILE, buf)
        # 設定データ
        buf = []
        for i, ch in enumerate(self.ch):
            buf.append(
                '    <setting label="{name}" type="bool" id="{id}" default="true" enable="eq({offset},2)" visible="true"/>'
                .format(id=ch['id'], name=ch['name'], offset=-1-i))
        # 設定データを書き込む
        write_file(self.SETTINGS_FILE, '\n'.join(buf))

    def getProgramData(self, renew=False):
        return [{'id': s['id'], 'progs': [{'title': s.get('onair','n/a')}]} for s in self.getStationData()]

    def beginEdit(self, id):
        ch = filter(lambda x:x['id']==id, self.getStationData())[0]
        Const.SET('id',id)
        Const.SET('name',ch['name'])
        Const.SET('stream',ch['url'])
        xbmc.executebuiltin('Addon.OpenSettings(%s)' % Const.ADDON_ID)
        xbmc.executebuiltin('SetFocus(103)') # select 4th category
        xbmc.executebuiltin('SetFocus(201)') # select 2nd control

    def endEdit(self, id, name, stream):
        if id == '':
            self.ch.append({'name':name, 'stream':stream})
        else:
            data = filter(lambda x:x['id']==id, self.getStationData())[0]
            ch = filter(lambda x:x['name']==data['name'] and x['stream']==data['url'], self.ch)[0]
            ch['name'] = name
            ch['stream'] = stream
        # 追加/編集した設定を書き込む
        self.write()
        # 変更を反映する
        self.setup(renew=True)
        # 設定ダイアログを更新する
        xbmc.executebuiltin('RunPlugin(%s?action=updateDialog)' % (sys.argv[0]))

    def delete(self, id):
        # 指定したidを除いた要素で配列を書き換える
        ch = filter(lambda x:x['id']==id, self.getStationData())[0]
        self.ch = filter(lambda x:x['name']!=ch['name'] or x['stream']!=ch['url'], self.ch)
        # 削除した設定を書き込む
        self.write()
        # 変更を反映する
        self.setup(renew=True)
        # 設定ダイアログを更新する
        xbmc.executebuiltin('RunPlugin(%s?action=updateDialog)' % (sys.argv[0]))
