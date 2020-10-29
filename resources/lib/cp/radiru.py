# -*- coding: utf-8 -*-

from ..const import Const
from ..common import *
from ..xmltodict import parse

import os
import xml.dom.minidom
import re
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
import exceptions
import json


class Params:
    # ファイルパス
    DATA_PATH = os.path.join(Const.DATA_PATH, 'radiru')
    if not os.path.isdir(DATA_PATH): os.makedirs(DATA_PATH)
    # ファイル
    PROGRAM_FILE  = os.path.join(DATA_PATH, 'program.json')
    STATION_FILE  = os.path.join(DATA_PATH, 'station.xml')
    SETTINGS_FILE = os.path.join(DATA_PATH, 'settings.xml')
    # URL
    STATION_URL   = 'https://www.nhk.or.jp/radio/config/config_web.xml'
    PROGRAM_URL   = 'https://api.nhk.or.jp/r2/pg/now/4/%s/netradio.json'
    # 地域
    AREA  = [
        ('東京', '130'),
        ('札幌', '010'),
        ('仙台', '040'),
        ('名古屋', '230'),
        ('大阪', '270'),
        ('広島', '340'),
        ('松山', '380'),
        ('福岡', '400'),
    ]
    # 放送局
    STATION  = [
        {
            'id':   'NHKR1',
            'name': 'NHKラジオ第1',
            'hls':  'r1hls',
            'logo': 'https://www.nhk.or.jp/common/img/media/r1-200x200.png',
            'id1':  'n1',
        },
        {
            'id':   'NHKR2',
            'name': 'NHKラジオ第2',
            'hls':  'r2hls',
            'logo': 'https://www.nhk.or.jp/common/img/media/r2-200x200.png',
            'id1':  'n2',
        },
        {
            'id':   'NHKFM',
            'name': 'NHK FM',
            'hls':  'fmhls',
            'logo': 'https://www.nhk.or.jp/common/img/media/fm-200x200.png',
            'id1':  'n3',
        }
    ]
    # 遅延
    LAG = 40


class Radiru(Params):

    def __init__(self, renew=False):
        self.id = 'radiru'
        try:
            area = Const.GET('area')
            self.areajp, self.areakey = self.AREA[int(area)]
        except:
            self.areajp, self.areakey = self.AREA[0]
        # 放送局データと設定データを初期化
        self.getStationFile(renew)

    def getStationFile(self, renew=False):
        # キャッシュがあれば何もしない
        if renew == False and os.path.isfile(self.STATION_FILE) and os.path.isfile(self.SETTINGS_FILE):
            return
        # キャッシュがなければウェブから読み込む
        data = urlread(self.STATION_URL)
        # データ変換
        dom = convert(parse(data))
        index = map(lambda x:x['areajp'], dom['radiru_config']['stream_url']['data']).index(self.areajp)
        station = dom['radiru_config']['stream_url']['data'][index]
        # 放送局データ
        buf = []
        for s in self.STATION:
            buf.append(
                '<station>'
                '<id>radiru_{id}</id>'
                '<name>{name}</name>'
                '<logo_large>{logo}</logo_large>'
                '<url>{url}</url>'
                '<lag>{lag}</lag>'
                '</station>'
                .format(id=s['id'], name=s['name'], logo=s['logo'], url=station[s['hls']], lag=self.LAG))
        # 放送局データを書き込む
        with open(self.STATION_FILE, 'w') as f:
            f.write('\n'.join(buf))
        # 設定データ
        buf = []
        for i, s in enumerate(self.STATION):
            buf.append('    <setting label="{name}" type="bool" id="radiru_{id}" default="true" enable="eq({offset},2)"/>'
                .format(id=s['id'], name=s['name'], offset=-1-i))
        # 設定データを書き込む
        with open(self.SETTINGS_FILE, 'w') as f:
            f.write('\n'.join(buf))

    def getStationData(self):
        with open(self.STATION_FILE, 'r') as f:
            stations = f.read()
        return stations

    def getSettingsData(self):
        with open(self.SETTINGS_FILE, 'r') as f:
            settings = f.read()
        return settings

    def getProgramFile(self):
        data = urlread(self.PROGRAM_URL % self.areakey)
        if data:
            write_json(self.PROGRAM_FILE, convert(json.loads(data)))

    def getProgramData(self, renew=False):
        if renew or not os.path.isfile(self.PROGRAM_FILE):
            self.getProgramFile()
        data = read_json(self.PROGRAM_FILE)
        data = convert(data, True)
        buf = []
        for s in self.STATION:
            progs = []
            # 放送中のプログラム
            for order in ('present','following'):
                # 時刻情報をパース
                try:
                    r = data['nowonair_list'][s['id1']][order]
                    t = r['start_time']
                    ft = str(t[0:4])+str(t[5:7])+str(t[8:10])+str(t[11:13])+str(t[14:16])+str(t[17:19])
                    ftl = str(t[11:13])+str(t[14:16])
                    t = r['end_time']
                    to = str(t[0:4])+str(t[5:7])+str(t[8:10])+str(t[11:13])+str(t[14:16])+str(t[17:19])
                    tol = str(t[11:13])+str(t[14:16])
                except exceptions.IndexError:
                    break
                except exceptions.KeyError:
                    continue
                # xml
                progs.append(
                    {
                        'ft': ft,
                        'ftl': ftl,
                        'to': to,
                        'tol': tol,
                        'title': r.get('title','n/a'),
                        'subtitle': r.get('subtitle',''),
                        'content': r.get('content',''),
                        'act': r.get('act',''),
                        'music': r.get('music',''),
                        'free': r.get('free','')
                    }
                )
            buf.append({'id':'radiru_%s' % s['id'], 'progs':progs})
        return buf
