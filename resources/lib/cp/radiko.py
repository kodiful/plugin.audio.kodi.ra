# -*- coding: utf-8 -*-

# radikoのプレーヤ(player.swf)をダウンロード
# player.swfに潜むRadikoPlayer_keyImageを抽出
# https://radiko.jp/v2/api/auth1_fmsへPOSTでアクセスしてauthtokenとKeyLength、KeyOffsetを取得
# KeyLength、KeyOffsetを基にRadikoPlayer_keyImageからバイナリデータを取得しBASE64で符号化(PartialKey)
# authtokenとPartialKeyをリクエストヘッダに載せてhttps://radiko.jp/v2/api/auth2_fmsへPOSTでアクセス
# 認証に成功すればauthtokenを使ってrtmpdumpでデータを受信

# cf. http://d.hatena.ne.jp/zariganitosh/20130124/rtmpdump_radiko_access

from common import Common

from ..const import Const
from ..common import *
from ..xmltodict import parse

import os
import struct
import zlib
import urllib, urllib2
import time
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

from base64 import b64encode
from math import ceil

class Params:
    # ファイルパス
    DATA_PATH = os.path.join(Const.DATA_PATH, 'radiko')
    if not os.path.isdir(DATA_PATH): os.makedirs(DATA_PATH)
    # ファイル
    KEY_FILE      = os.path.join(DATA_PATH, 'authkey.dat')
    PLAYER_FILE   = os.path.join(DATA_PATH, 'player.swf')
    # ファイル
    PROGRAM_FILE  = os.path.join(DATA_PATH, 'program.xml')
    STATION_FILE  = os.path.join(DATA_PATH, 'station.json')
    SETTINGS_FILE = os.path.join(DATA_PATH, 'settings.xml')
    # URL
    AUTH1_URL     = 'https://radiko.jp/v2/api/auth1_fms'
    AUTH2_URL     = 'https://radiko.jp/v2/api/auth2_fms'
    PLAYER_URL    = 'http://radiko.jp/apps/js/flash/myplayer-release.swf'
    STATION_URL   = 'http://radiko.jp/v2/station/list/%s.xml'
    REFERER_URL   = 'http://radiko.jp/player/timetable.html'
    PROGRAM_URL   = 'http://radiko.jp/v2/api/program/now?area_id=%s'
    STREAM_URL    = 'rtmpe://f-radiko.smartstream.ne.jp'
    # 遅延
    DELAY         = 3
    # その他
    OBJECT_TAG    = 87
    OBJECT_ID     = 12


class Authkey:

    def __init__(self, renew=False):
        if renew or not os.path.isfile(Params.KEY_FILE):
            # PLAYER_URLのオブジェクトのサイズを取得
            try:
                response = urllib2.urlopen(Params.PLAYER_URL)
                size = int(response.headers["content-length"])
            except Exception as e:
                log(str(e), error=True)
                return
            # PLAYERファイルのサイズと比較、異なっている場合はダウンロードしてKEYファイルを生成
            if not os.path.isfile(Params.PLAYER_FILE) or size != int(os.path.getsize(Params.PLAYER_FILE)):
                swf = response.read()
                with open(Params.PLAYER_FILE, 'wb') as f:
                    f.write(swf)
                # 読み込んだswfバッファ
                self.swf = swf[:8] + zlib.decompress(swf[8:])
                # swf読み込みポインタ
                self.pos = 0
                # ヘッダーパース
                self.__header()
                # タブブロックがある限り
                while self.__block():
                    log(self.block['tag'], self.block['block_len'], self.block['id'])
                    if self.block['tag'] == Params.OBJECT_TAG and self.block['id'] == Params.OBJECT_ID:
                        with open(Params.KEY_FILE, 'wb') as f:
                            f.write(self.block['value'])
                        break

    # ヘッダーパース
    def __header(self):
        self.magic   = self.__read(3)
        self.version = ord(self.__read(1))
        self.file_length = self.__le4Byte(self.__read(4))
        rectbits = ord(self.__read(1)) >> 3
        total_bytes = int(ceil((5 + rectbits * 4) / 8.0))
        twips_waste = self.__read(total_bytes - 1)
        self.frame_rate_decimal = ord(self.__read(1))
        self.frame_rate_integer = ord(self.__read(1))
        self.frame_count = self.__le2Byte(self.__read(2))
        log('magic:{magic}, version:{version}, length:{length}, frame_rate:{fr_integer}.{fr_decimal}, count:{fr_count}'.format(
            magic = self.magic,
            version = self.version,
            length = self.file_length,
            fr_integer = self.frame_rate_integer,
            fr_decimal = self.frame_rate_decimal,
            fr_count = self.frame_count))

    # ブロック判定
    def __block(self):
        blockStart = self.pos
        tag = self.__le2Byte(self.__read(2))
        blockLen = tag & 0x3f
        if blockLen == 0x3f:
            blockLen = self.__le4Byte(self.__read(4))
        tag = tag >> 6
        if tag == 0:
            return None
        else:
            self.blockPos = 0
            self.block = {
                'block_start': blockStart,
                'tag': tag,
                'block_len': blockLen,
                'id': self.__le2Byte(self.__read(2)),
                'alpha': self.__read(4),
                'value': self.__read(blockLen-6) or None
            }
            return True

    # ユーティリティ
    def __read(self, num):
        self.pos += num
        return self.swf[self.pos - num: self.pos]

    def __le2Byte(self, s):
        # LittleEndian to 2 Byte
        return struct.unpack('<H', s)[0]

    def __le4Byte(self, s):
        # LittleEndian to 4 Byte
        return struct.unpack('<L', s)[0]


class Authenticate:

    def __init__(self):
        # 初期化
        self.response = response = {'auth_token':'', 'area_id':'', 'authed':0}
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
                log('failed to get area_id')
        else:
            log('failed to get auth_token')

    def appIDAuth(self, response):
        # ヘッダ
        headers = {
            'pragma': 'no-cache',
            'X-Radiko-App': 'pc_ts',
            'X-Radiko-App-Version': '4.0.0',
            'X-Radiko-User': 'test-stream',
            'X-Radiko-Device': 'pc'
        }
        try:
            # リクエスト
            req = urllib2.Request(Params.AUTH1_URL, headers=headers, data='\r\n')
            # レスポンス
            auth1fms = urllib2.urlopen(req).info()
        except Exception as e:
            log(str(e), error=True)
            return
        response['auth_token'] = auth1fms['X-Radiko-AuthToken']
        response['key_offset'] = int(auth1fms['X-Radiko-KeyOffset'])
        response['key_length'] = int(auth1fms['X-Radiko-KeyLength'])
        # ログ
        log('authtoken:{authtoken}, offset:{offset}, length:{length}'.format(
            authtoken = response['auth_token'],
            offset = response['key_offset'],
            length = response['key_length']))
        return response

    def challengeAuth(self, response):
        # ヘッダ
        response['partial_key'] = self.createPartialKey(response)
        headers = {
            'pragma': 'no-cache',
            'X-Radiko-App': 'pc_ts',
            'X-Radiko-App-Version': '4.0.0',
            'X-Radiko-User': 'test-stream',
            'X-Radiko-Device': 'pc',
            'X-Radiko-Authtoken': response['auth_token'],
            'X-Radiko-Partialkey': response['partial_key']
        }
        try:
            # リクエスト
            req = urllib2.Request(Params.AUTH2_URL, headers=headers, data='\r\n')
            # レスポンス
            auth2fms = urllib2.urlopen(req).read().decode('utf-8')
        except Exception as e:
            log(str(e), error=True)
            return
        response['area_id'] = auth2fms.split(',')[0].strip()
        # ログ
        log('authtoken:{authtoken}, offset:{offset}, length:{length} partialkey:{partialkey}'.format(
            authtoken = response['auth_token'],
            offset = response['key_offset'],
            length = response['key_length'],
            partialkey = response['partial_key']))
        return response

    def createPartialKey(self, response):
        f = open(Params.KEY_FILE, 'rb')
        f.seek(response['key_offset'])
        partialkey = b64encode(f.read(response['key_length'])).decode('utf-8')
        f.close()
        return partialkey


class Radiko(Params, Common):

    def __init__(self, area, token, renew=False):
        self.id = 'radiko'
        self.area = area
        self.token = token
        # 放送局データと設定データを初期化
        if self.area and self.token:
            self.setup(renew)

    def setup(self, renew=False):
        # キャッシュがあれば何もしない
        if renew == False and os.path.isfile(self.STATION_FILE) and os.path.isfile(self.SETTINGS_FILE):
            return
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
                    'logo_large': s['logo_large'],
                    'url': '%s/%s/_definst_/simul-stream.stream live=1 conn=S: conn=S: conn=S: conn=S:%s' % (self.STREAM_URL, s['id'], self.token),
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
        # キャッシュを確認
        if renew or not os.path.isfile(self.PROGRAM_FILE):
            # キャッシュがなければウェブから読み込む
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
        # データ抽出
        data = read_file(self.PROGRAM_FILE)
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
                        'subtitle': p.get('subtitle',''),
                        'content': p.get('content',''),
                        'act': p.get('act',''),
                        'music': p.get('music',''),
                        'free': p.get('free','')
                    })
                buf.append({'id':'radiko_%s' % s['@id'], 'progs':progs})
            return buf
        else:
            return []
