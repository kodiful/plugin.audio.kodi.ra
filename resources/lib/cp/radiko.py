# -*- coding: utf-8 -*-

from jcba import Jcba

from ..const import Const
from ..common import *
from ..xmltodict import parse

import os
import time, datetime
import urllib, urllib2
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

from base64 import b64encode


class Params:
    # ファイルパス
    DATA_PATH = os.path.join(Const.DATA_PATH, 'radiko')
    if not os.path.isdir(DATA_PATH): os.makedirs(DATA_PATH)
    # ファイル
    PROGRAM_FILE  = os.path.join(DATA_PATH, 'program.xml')
    STATION_FILE  = os.path.join(DATA_PATH, 'station.json')
    SETTINGS_FILE = os.path.join(DATA_PATH, 'settings.xml')
    NEXTUPDT_FILE = os.path.join(DATA_PATH, 'nextupdt.json')
    # URL
    STATION_URL   = 'http://radiko.jp/v2/station/list/%s.xml'
    REFERER_URL   = 'http://radiko.jp/player/timetable.html'
    PROGRAM_URL   = 'http://radiko.jp/v2/api/program/now?area_id=%s'
    STREAM_URL    = 'https://f-radiko.smartstream.ne.jp/%s/_definst_/simul-stream.stream/playlist.m3u'
    # プロキシ
    PROXY_ID      = 'script.local.proxy'
    # 遅延
    DELAY         = 3


class Authenticate:

    # ファイル
    PLAYER_FILE  = os.path.join(Params.DATA_PATH, 'player.js')
    AUTHKEY_FILE = os.path.join(Params.DATA_PATH, 'authkey.txt')
    # URL
    PLAYER_URL   = 'https://radiko.jp/apps/js/playerCommon.js'
    AUTH1_URL    = 'https://radiko.jp/v2/api/auth1'
    AUTH2_URL    = 'https://radiko.jp/v2/api/auth2'

    def __init__(self, renew=True):
        # プレイヤーを取得
        if renew or not os.path.isfile(self.PLAYER_FILE):
            self.getPlayerFile()
        # authkeyを取得してresponseを初期化
        self.response = response = {'auth_key':self.getAuthKey(), 'auth_token':'', 'area_id':'', 'authed':0}
        if response['auth_key']:
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
        else:
            log('getAuthKey failed.')

    # auth_keyを取得
    def getPlayerFile(self):
        # PLAYERファイルを取得する
        try:
            # リクエスト
            req = urllib2.Request(self.PLAYER_URL)
            # レスポンス
            res = urllib2.urlopen(req)
        except Exception as e:
            log(str(e), error=True)
            return
        # PLAYERファイルからauthkeyを抽出して保存
        if res.code == 200:
            # ファイル変更日時
            mod = strptime(res.info().get('Last-Modified'), '%a, %d %b %Y %H:%M:%S GMT')
            if os.path.isfile(self.PLAYER_FILE):
                # 更新されていない場合はなにもしない
                if mod <= datetime.datetime.fromtimestamp(int(os.path.getmtime(self.PLAYER_FILE))):
                    return
            # PLAYERをダウンロードしてファイルに書き込む
            player = res.read()
            write_file(self.PLAYER_FILE, player)
            # タイムスタンプをLast-Modifiedの日時に設定する
            os.utime(self.PLAYER_FILE, (-1, int(time.mktime(mod.timetuple()))))
            # PLAYERファイルからauthkeyを取得
            # player = new RadikoJSPlayer($audio[0], 'pc_html5', 'bcd151073c03b352e1ef2fd66c32209da9ca0afa', {
            match = re.search(r'new\s+RadikoJSPlayer\(.*?,\s+\'(.*?)\',\s+\'(.*?)\',', player)
            authkey = match.group(2) if match else ''
            write_file(self.AUTHKEY_FILE, authkey)
            log('player and authkey updated')
        else:
            log('player nor authkey unchanged (%d)' % res.code)

    # authkeyを取得
    def getAuthKey(self):
        return read_file(self.AUTHKEY_FILE) or ''

    # auth_tokenを取得
    def appIDAuth(self, response):
        # ヘッダ
        headers = {
            'x-radiko-device': 'pc',
            'x-radiko-app-version': '0.0.1',
            'x-radiko-user': 'dummy_user',
            'x-radiko-app': 'pc_html5'
        }
        try:
            # リクエスト
            req = urllib2.Request(self.AUTH1_URL, headers=headers)
            # レスポンス
            auth1 = urllib2.urlopen(req).info()
        except Exception as e:
            log(str(e), error=True)
            return
        response['auth_token'] = auth1['X-Radiko-AuthToken']
        response['key_offset'] = int(auth1['X-Radiko-KeyOffset'])
        response['key_length'] = int(auth1['X-Radiko-KeyLength'])
        return response

    # partialkeyを取得
    def createPartialKey(self, response):
        partial_key = response['auth_key'][response['key_offset']:response['key_offset']+response['key_length']]
        return b64encode(partial_key)

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
        try:
            # リクエスト
            req = urllib2.Request(self.AUTH2_URL, headers=headers)
            # レスポンス
            auth2 = urllib2.urlopen(req).read().decode('utf-8')
        except Exception as e:
            log(str(e), error=True)
            return
        response['area_id'] = auth2.split(',')[0].strip()
        return response


class Radiko(Params, Jcba):

    def __init__(self, area, token, renew=False):
        self.area = area
        self.token = token
        # 放送局データと設定データを初期化
        if self.area and self.token:
            self.setup(renew)

    def setup(self, renew=False):
        # キャッシュがあれば何もしない
        if renew == False and os.path.isfile(self.STATION_FILE) and os.path.isfile(self.SETTINGS_FILE):
            return
        # プロキシ設定
        try:
            addon = xbmcaddon.Addon(self.PROXY_ID)
            port = addon.getSetting('port')
            port = int(port)
        except:
            notify('Local proxy required to play Radiko', 3000)
            port = 0
        # キャッシュがなければウェブから読み込む
        data = urlread(self.STATION_URL % self.area)
        if data:
            # データ変換
            dom = convert(parse(data))
            station = dom['stations'].get('station',[]) if dom['stations'] else []
            station = station if isinstance(station,list) else [station]
            # 放送局データ
            buf = []
            for s in station:
                buf.append({
                    'id': 'radiko_%s' % s['id'],
                    'name': s['name'],
                    'url': s['href'],
                    'logo_large': s['logo_large'],
                    'stream': 'http://127.0.0.1:%d/%s' % (int(port), urllib.urlencode({'X-Radiko-AuthToken':self.token, '_':self.STREAM_URL % s['id']})) if port else '',
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
                        offset=-1-i))
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
                url = self.PROGRAM_URL % self.area
                if self.area:
                    data = urlread(url, {'Referer':self.REFERER_URL})
                    write_file(self.PROGRAM_FILE, data)
                else:
                    raise urllib2.URLError
            except:
                write_file(self.PROGRAM_FILE, '')
                log('failed to get data from url:%s' % url)
        # キャッシュから番組データを抽出
        data = data or read_file(self.PROGRAM_FILE)
        if data:
            dom = convert(parse(data))
            buf = []
            # 放送局
            station = dom['radiko']['stations']['station']
            station = station if isinstance(station,list) else [station]
            for s in station:
                progs = []
                # 放送中のプログラム
                program = s['scd']['progs']['prog']
                program = program if isinstance(program,list) else [program]
                for p in program:
                    progs.append({
                        'ft': p.get('@ft',''),
                        'ftl': p.get('@ftl',''),
                        'to': p.get('@to',''),
                        'tol': p.get('@tol',''),
                        'title': p.get('title','n/a'),
                        'subtitle': p.get('sub_title',''),
                        'pfm': p.get('pfm',''),
                        'desc': p.get('desc',''),
                        'info': p.get('info',''),
                        'url': p.get('url',''),
                        'content': p.get('content',''),
                        'act': p.get('act',''),
                        'music': p.get('music',''),
                        'free': p.get('free','')
                    })
                results.append({'id':'radiko_%s' % s['@id'], 'progs':progs})
                buf += progs
            # 次の更新時刻
            nextupdate = self.getNextUpdate(buf)
        # 次の更新時刻をファイルに書き込む
        write_file(self.NEXTUPDT_FILE, nextupdate)
        return results, nextupdate
