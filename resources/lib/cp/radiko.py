# -*- coding: utf-8 -*-

from resources.lib.cp.jcba import Jcba

from resources.lib.const import Const
from resources.lib.common import log
from resources.lib.common import timestamp
from resources.lib.common import urlread
from resources.lib.common import read_file
from resources.lib.common import write_file
from resources.lib.common import write_json
from resources.lib.localproxy import LocalProxy

from xmltodict import parse

import os
import urllib

import math
import random
from base64 import b64encode, b64decode


class Params:
    # ファイルパス
    DATA_PATH = os.path.join(Const.DATA_PATH, 'radiko')
    if not os.path.isdir(DATA_PATH):
        os.makedirs(DATA_PATH)
    # ファイル
    PROGRAM_FILE = os.path.join(DATA_PATH, 'program.xml')
    STATION_FILE = os.path.join(DATA_PATH, 'station.json')
    SETTINGS_FILE = os.path.join(DATA_PATH, 'settings.xml')
    NEXTUPDT_FILE = os.path.join(DATA_PATH, 'nextupdt.json')
    # URL
    STATION_URL = 'http://radiko.jp/v2/station/list/%s.xml'
    REFERER_URL = 'http://radiko.jp/player/timetable.html'
    PROGRAM_URL = 'http://radiko.jp/v2/api/program/now?area_id=%s'
    STREAM_URL = 'https://f-radiko.smartstream.ne.jp/%s/_definst_/simul-stream.stream/playlist.m3u'
    # 遅延
    DELAY = 20

    STN = 'radiko_'


class Authenticate:
    # [kojira](https://github.com/jackyzy823/rajiko) を元に，エリアフリー化。
    # キー
    AUTH_KEY = 'bcd151073c03b352e1ef2fd66c32209da9ca0afa'
    # URL
    AUTH1_URL = 'https://radiko.jp/v2/api/auth1'
    AUTH2_URL = 'https://radiko.jp/v2/api/auth2'

    def __init__(self, renew=True):
        # responseを初期化
        self.response = response = {'auth_key': self.AUTH_KEY, 'auth_token': '', 'area_id': '', 'authed': 0}
        self.info = info = { 'appversion': '', 'userid': '', 'useragent': '', 'device': '' }
        
        # radikoの設定取得
        regi = int(Const.GET('radikoregion')) if Const.GET('radikoregion') != '' else 0
        area = 0
        area_id = ''
        if regi > 0: # Auto以外
            area = int(Const.GET('radikoarea' + str(regi)))
            area_id = Const.areaListParRegion[ Const.regions[regi - 1]['id'] ][area]['id'] # JPxx
            self.info = info = self.genRandomInfo()
            self.response = response = {'auth_key': Const.fullkey_b64, 'auth_token': '', 'area_id': area_id, 'authed': 0}
        log('region:%s area:%s => %s' % (regi, area, area_id))

        # auth_tokenを取得
        response = self.appIDAuth(response)
        if response and response['auth_token']:
            # area_idを取得
            response = self.challengeAuth(response)
            if response and response['area_id']:
                response['authed'] = 1
                # インスタンス変数に格納
                self.response = response
            else:
                log('challengeAuth failed.')
        else:
            log('appIDAuth failed.')

    # auth_tokenを取得
    def appIDAuth(self, response):
        # ヘッダ
        headers = {
            'x-radiko-device': 'pc',
            'x-radiko-app-version': '0.0.1',
            'x-radiko-user': 'dummy_user',
            'x-radiko-app': 'pc_html5'            
        }
        if response['area_id'] != '':
            headers = {
                'User-Agent': self.info['useragent'],
                'X-Radiko-App': 'aSmartPhone7a',
                'X-Radiko-App-Version': self.info['userid'],
                'X-Radiko-Device': self.info['device'],
                'X-Radiko-User': self.info['userid']
            }
        try:
            # リクエスト
            req = urllib.request.Request(self.AUTH1_URL, headers=headers)
            # レスポンス
            auth1 = urllib.request.urlopen(req).info()
        except Exception as e:
            log('AUTH1: ' + str(e), error=True)
            return
        response['auth_token'] = auth1['X-Radiko-AuthToken']
        response['key_offset'] = int(auth1['X-Radiko-KeyOffset'])
        response['key_length'] = int(auth1['X-Radiko-KeyLength'])
        return response

    # partialkeyを抽出
    def createPartialKey(self, response):
        ret = ''
        if response['area_id'] != '':
            partial_key = b64decode(response['auth_key'])[response['key_offset']:response['key_offset'] + response['key_length']]
            ret = b64encode(partial_key).decode()
        else:
            partial_key = response['auth_key'][response['key_offset']:response['key_offset'] + response['key_length']]
            ret = b64encode(partial_key.encode()).decode()
        return ret

    # area_idを取得
    def challengeAuth(self, response):
        # ヘッダ
        response['partial_key'] = self.createPartialKey(response)
        headers = {
            'x-radiko-authtoken': response['auth_token'],
            'x-radiko-device': 'pc',
            'x-radiko-partialkey': response['partial_key'],
            'x-radiko-user': 'dummy_user'
        }
        if response['area_id'] != '':
            headers = {
                'User-Agent': self.info['useragent'],
                'X-Radiko-App': 'aSmartPhone7a',
                'X-Radiko-App-Version': self.info['userid'],
                'X-Radiko-Device': self.info['device'],
                'X-Radiko-User': self.info['userid'],

                'X-Radiko-AuthToken': response['auth_token'],
                'X-Radiko-Location': self.genGPS(response['area_id']),
                'X-Radiko-Connection': "wifi",
                'X-Radiko-Partialkey': response['partial_key']
            }
        try:
            # リクエスト
            req = urllib.request.Request(self.AUTH2_URL, headers=headers)
            # レスポンス
            auth2 = urllib.request.urlopen(req).read().decode()
        except Exception as e:
            log('AUTH2: ' + str(e), error=True)
            return
        response['area_id'] = auth2.split(',')[0].strip()
        return response

    # 所在偽装(rajiko)
    def genGPS(self, area_id):
        ret = ''
        latlong = Const.coordinates[ Const.areaList[ int(area_id[2:]) - 1 ] ]
        lat = latlong[0]
        long = latlong[1]
        # +/- 0 ~ 0.025 --> 0 ~ 1.5' ->  +/-  0 ~ 2.77/2.13km
        lat = lat + random.random() / 40.0 * (1 if random.random() > 0.5 else -1)
        long = long + random.random() / 40.0 * (1 if random.random() > 0.5 else -1)
        ret = '{:.6f}'.format(lat) + ',' + '{:.6f}'.format(long) + ',gps'
        return ret

    # 端末情報偽装(rajiko)
    def genRandomInfo(self):
        version = list(Const.VERSION_MAP.keys())[ math.floor(random.random() * len(Const.VERSION_MAP)) ]
        sdk =   Const.VERSION_MAP[version]['sdk']
        build = Const.VERSION_MAP[version]['builds'][ math.floor(random.random() * len(Const.VERSION_MAP[version]['builds'])) ]

        model = Const.MODEL_LIST[ math.floor(random.random() * len(Const.MODEL_LIST)) ]
        device = sdk + "." + model

        useragent = 'Dalvik/2.1.0 (Linux; U; Android ' + version + '; ' + model + '/' + build + ')'

        appver = ["7.3.7","7.3.6","7.3.5","7.3.4","7.3.3","7.3.2","7.3.1","7.3.0","7.2.11","7.2.10","7.2.1","7.2.0","7.1.13","7.1.1","7.1.0","7.0.9","6.4.7","6.4.6"]
        appversion = appver[ math.floor(random.random() * len(appver)) ]

        hex = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f']
        s = ''
        for i in range(32):
            s += hex[ math.floor(random.random() * len(hex)) ]
        userid = s

        return {
            'appversion': appversion,
            'userid': userid,
            'useragent': useragent,
            'device': device
        }


class Radiko(Params, Jcba):

    def __init__(self, area, token, renew=False):
        self.area = area
        self.token = token
        # 放送局データと設定データを初期化
        if self.area and self.token:
            self.setup(renew)

    def setup(self, renew=False):
        # キャッシュがあれば何もしない
        if renew is False and os.path.isfile(self.STATION_FILE) and os.path.isfile(self.SETTINGS_FILE):
            return
        # キャッシュがなければウェブから読み込む
        data = urlread(self.STATION_URL % self.area)
        if data:
            # データ変換
            dom = parse(data)
            station = dom['stations'].get('station', []) if dom['stations'] else []
            station = station if isinstance(station, list) else [station]
            # 放送局データ
            buf = []
            for s in station:
                buf.append({
                    'id': 'radiko_%s' % s['id'],
                    'name': s['name'],
                    'url': s['href'],
                    'logo_large': s['logo_large'],
                    'stream': LocalProxy.proxy(self.STREAM_URL % s['id'], {'x-radiko-authtoken': self.token}),
                    'delay': self.DELAY
                })
            # 放送局データを書き込む
            write_json(self.STATION_FILE, buf)
            # 設定データ
            buf = []
            for i, s in enumerate(station):
                buf.append(
                    '    <setting label="{name}" type="bool" id="radiko_{id}" default="true" enable="eq({offset},2)"/>'.format(
                        id=s['id'],
                        name=s['name'],
                        offset=-1 - i))
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
        nextupdate = '0' * 14
        # キャッシュを確認
        if renew or not os.path.isfile(self.PROGRAM_FILE) or timestamp() > read_file(self.NEXTUPDT_FILE):
            # ウェブから読み込む
            try:
                url = self.PROGRAM_URL % self.area
                if self.area:
                    data = urlread(url, {'Referer': self.REFERER_URL})
                    write_file(self.PROGRAM_FILE, data)
                else:
                    raise urllib.error.URLError
            except Exception:
                write_file(self.PROGRAM_FILE, '')
                log('failed to get data from url:%s' % url)
        # キャッシュから番組データを抽出
        data = data or read_file(self.PROGRAM_FILE)
        if data is not None:
            dom = parse(data)
            buf = []
            # 放送局
            station = dom['radiko']['stations']['station']
            station = station if isinstance(station, list) else [station]
            for s in station:
                progs = []
                # 放送中のプログラム
                program = s['scd']['progs']['prog']
                program = program if isinstance(program, list) else [program]
                for p in program:
                    progs.append({
                        'ft': p.get('@ft', ''),
                        'ftl': p.get('@ftl', ''),
                        'to': p.get('@to', ''),
                        'tol': p.get('@tol', ''),
                        'title': p.get('title', 'n/a'),
                        'subtitle': p.get('sub_title', ''),
                        'pfm': p.get('pfm', ''),
                        'desc': p.get('desc', ''),
                        'info': p.get('info', ''),
                        'url': p.get('url', ''),
                        'content': p.get('content', ''),
                        'act': p.get('act', ''),
                        'music': p.get('music', ''),
                        'free': p.get('free', '')
                    })
                results.append({'id': 'radiko_%s' % s['@id'], 'progs': progs})
                buf += progs
            # 次の更新時刻
            nextupdate = self.getNextUpdate(buf)
        # 次の更新時刻をファイルに書き込む
        write_file(self.NEXTUPDT_FILE, nextupdate)
        return results, nextupdate
