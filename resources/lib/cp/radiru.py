# -*- coding: utf-8 -*-

from jcba import Jcba

from resources.lib.const import Const
from resources.lib.common import *

from xmltodict import parse

import os
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
    STATION_FILE  = os.path.join(DATA_PATH, 'station.json')
    SETTINGS_FILE = os.path.join(DATA_PATH, 'settings.xml')
    NEXTUPDT_FILE = os.path.join(DATA_PATH, 'nextupdt.json')
    # URL
    STATION_URL   = 'https://www.nhk.or.jp/radio/config/config_web.xml'
    PROGRAM_URL   = 'https://api.nhk.or.jp/r2/pg/now/4/%s/netradio.json'
    DEFAULT_URL   = 'https://www.nhk.or.jp/radio'
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
    DELAY = 40


class Radiru(Params, Jcba):

    def __init__(self, renew=False):
        try:
            area = Const.GET('area')
            self.areajp, self.areakey = self.AREA[int(area)]
        except:
            self.areajp, self.areakey = self.AREA[0]
        # 放送局データと設定データを初期化
        self.setup(renew)

    def setup(self, renew=False):
        # キャッシュがあれば何もしない
        if renew == False and os.path.isfile(self.STATION_FILE) and os.path.isfile(self.SETTINGS_FILE):
            return
        # キャッシュがなければウェブから読み込む
        data = urlread(self.STATION_URL)
        if data:
            # データ変換
            dom = convert(parse(data))
            index = map(lambda x:x['areajp'], dom['radiru_config']['stream_url']['data']).index(self.areajp)
            station = dom['radiru_config']['stream_url']['data'][index]
            # 放送局データ
            buf = []
            for s in self.STATION:
                buf.append({
                    'id': 'radiru_%s' % s['id'],
                    'name': s['name'],
                    'url': self.DEFAULT_URL,
                    'logo_large': s['logo'],
                    'stream': station[s['hls']],
                    'delay': self.DELAY
                })
            # 放送局データを書き込む
            write_json(self.STATION_FILE, buf)
            # 設定データ
            buf = []
            for i, s in enumerate(self.STATION):
                buf.append('    <setting label="{name}" type="bool" id="radiru_{id}" default="true" enable="eq({offset},2)"/>'
                    .format(id=s['id'], name=s['name'], offset=-1-i))
            # 設定データを書き込む
            write_file(self.SETTINGS_FILE, '\n'.join(buf))
        else:
            # 放送局データを書き込む
            write_json(self.STATION_FILE, [])
            # 設定データを書き込む
            write_file(self.SETTINGS_FILE, '')

    def getProgramData(self, renew=False):
        # 初期化
        data = ''
        results = []
        nextupdate = '0'*14
        # キャッシュを確認
        if renew or not os.path.isfile(self.PROGRAM_FILE) or timestamp() > read_file(self.NEXTUPDT_FILE):
            # ウェブから読み込む
            try:
                url = self.PROGRAM_URL % self.areakey
                data = urlread(url)
                write_json(self.PROGRAM_FILE, convert(json.loads(data)))
            except:
                write_file(self.PROGRAM_FILE, '')
                log('failed to get data from url:%s' % url)
        # キャッシュから番組データを抽出
        data = data or read_file(self.PROGRAM_FILE)
        if data:
            data = convert(json.loads(data), strip=True)
            buf = []
            for s in self.STATION:
                progs = []
                # 放送中のプログラム
                for order in ('present','following'):
                    # 時刻情報をパース
                    try:
                        p = data['nowonair_list'][s['id1']][order]
                        t = p['start_time']
                        ft = str(t[0:4])+str(t[5:7])+str(t[8:10])+str(t[11:13])+str(t[14:16])+str(t[17:19])
                        ftl = str(t[11:13])+str(t[14:16])
                        t = p['end_time']
                        to = str(t[0:4])+str(t[5:7])+str(t[8:10])+str(t[11:13])+str(t[14:16])+str(t[17:19])
                        tol = str(t[11:13])+str(t[14:16])
                    except exceptions.IndexError:
                        break
                    except exceptions.KeyError:
                        continue
                    progs.append({
                        'ft': ft,
                        'ftl': ftl,
                        'to': to,
                        'tol': tol,
                        'title': p.get('title','n/a'),
                        'subtitle': p.get('subtitle',''),
                        'pfm': p.get('pfm',''),
                        'desc': p.get('desc',''),
                        'info': p.get('info',''),
                        #
                        # "url": {
                        #   "e": "http://p.nhk.jp/radionews/",
                        #   "i": "http://p.nhk.jp/radionews/",
                        #   "pc": "http://www.nhk.or.jp/radionews/",
                        #   "short": "https://nhk.jp/P1336",
                        #   "v": "http://p.nhk.jp/radionews/"
                        # }
                        #
                        #'url': p.get('url',''),
                        'url': p.get('url') and p.get('url').get('pc') or '',
                        'content': p.get('content',''),
                        'act': p.get('act',''),
                        'music': p.get('music',''),
                        'free': p.get('free','')
                    })
                results.append({'id':'radiru_%s' % s['id'], 'progs':progs})
                buf += progs
            # 次の更新時刻
            nextupdate = self.getNextUpdate(buf)
        # 次の更新時刻をファイルに書き込む
        write_file(self.NEXTUPDT_FILE, nextupdate)
        return results, nextupdate
