# -*- coding: utf-8 -*-

# radikoのプレーヤ(player.swf)をダウンロード
# player.swfに潜むRadikoPlayer_keyImageを抽出
# https://radiko.jp/v2/api/auth1_fmsへPOSTでアクセスしてauthtokenとKeyLength、KeyOffsetを取得
# KeyLength、KeyOffsetを基にRadikoPlayer_keyImageからバイナリデータを取得しBASE64で符号化(PartialKey)
# authtokenとPartialKeyをリクエストヘッダに載せてhttps://radiko.jp/v2/api/auth2_fmsへPOSTでアクセス
# 認証に成功すればauthtokenを使ってrtmpdumpでデータを受信

# cf. http://d.hatena.ne.jp/zariganitosh/20130124/rtmpdump_radiko_access

from ..const import Const
from ..common import *
from ..xmltodict import parse

import os
import struct
import zlib
import urllib, urllib2
import xml.dom.minidom
import threading, time
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
    STATION_FILE  = os.path.join(DATA_PATH, 'station.xml')
    SETTINGS_FILE = os.path.join(DATA_PATH, 'settings.xml')
    # URL
    AUTH1_URL     = 'https://radiko.jp/v2/api/auth1_fms'
    AUTH2_URL     = 'https://radiko.jp/v2/api/auth2_fms'
    #PLAYER_URL    = 'http://radiko.jp/player/swf/player_3.0.0.01.swf'
    PLAYER_URL    = 'http://radiko.jp/apps/js/flash/myplayer-release.swf'
    STATION_URL   = 'http://radiko.jp/v2/station/list/'
    REFERER_URL   = 'http://radiko.jp/player/timetable.html'
    PROGRAM_URL   = 'http://radiko.jp/v2/api/program/now'
    STREAM_URL    = 'rtmpe://f-radiko.smartstream.ne.jp'
    # 遅延
    LAG           = 3
    # その他
    OBJECT_TAG    = 87
    #OBJECT_ID     = 14
    OBJECT_ID     = 12


#-------------------------------------------------------------------------------
class getAuthkey(Params, object):

    def __init__(self):

        while True:
            try:
                response = urllib2.urlopen(self.PLAYER_URL)
                UrlSize = int(response.headers["content-length"])
            except : UrlSize = 0

            if os.path.exists(self.PLAYER_FILE) : PathSize = int(os.path.getsize(self.PLAYER_FILE))
            else : PathSize = 0

            if UrlSize > 0 and UrlSize != PathSize:
                if os.path.exists(self.PLAYER_FILE) : os.remove(self.PLAYER_FILE)
                if os.path.exists(self.KEY_FILE) : os.remove(self.KEY_FILE)
                open(self.PLAYER_FILE, 'wb').write(response.read())
                self.keyFileDump()

            elif not os.path.exists(self.KEY_FILE) and PathSize > 0 :
                self.keyFileDump()

            if os.path.exists(self.KEY_FILE) : break
            else : time.sleep(1)

    #-----------------------------------
    def keyFileDump(self):
        tmpSwf = open(self.PLAYER_FILE, 'rb').read()
        self.Swf = tmpSwf[:8] + zlib.decompress(tmpSwf[8:]) # 読み込んだswfバッファ
        self.SwfPos = 0 # swf読み込みポインタ

        self.parseSwfHead()
        self.output_file = self.KEY_FILE
        while self.swfBlock(): # タブブロックがある限り
            #if __debug__: print (self.Block['tag'], self.Block['block_len'], self.Block['id'])
            log(self.Block['tag'], self.Block['block_len'], self.Block['id'])

            if self.Block['tag'] == self.OBJECT_TAG and self.Block['id'] == self.OBJECT_ID:
                self.Save(self.KEY_FILE)
                break

    #-----------------------------------
    # ヘッダーパース
    def parseSwfHead(self):
        global CMN
        self.magic   = self.swfRead(3)
        self.version = ord(self.swfRead(1))
        self.file_length = self.le4Byte(self.swfRead(4))

        rectbits = ord(self.swfRead(1)) >> 3
        total_bytes = int(ceil((5 + rectbits * 4) / 8.0))
        twips_waste = self.swfRead(total_bytes - 1)
        self.frame_rate_decimal = ord(self.swfRead(1))
        self.frame_rate_integer = ord(self.swfRead(1))
        self.frame_count = self.le2Byte(self.swfRead(2))

        '''if __debug__:
            print ("magic: %s\nver: %d\nlen: %d\nframe_rate: %d.%d\ncount: %d\n" % ( \
                self.magic,
                self.version,
                self.file_length,
                self.frame_rate_integer,
                self.frame_rate_decimal,
                self.frame_count))'''
        log("magic: %s, ver: %d, len: %d, frame_rate: %d.%d, count: %d" % ( \
            self.magic,
            self.version,
            self.file_length,
            self.frame_rate_integer,
            self.frame_rate_decimal,
            self.frame_count))

    #-----------------------------------
    # ブロック判定
    def swfBlock(self):
        # print "--SwfPos:", self.SwfPos
        SwfBlockStart = self.SwfPos
        SwfTag = self.le2Byte(self.swfRead(2))
        BlockLen = SwfTag & 0x3f
        if BlockLen == 0x3f:
            BlockLen = self.le4Byte(self.swfRead(4))
        SwfTag = SwfTag >> 6

        if SwfTag == 0:
            return None

        self.BlockPos = 0
        ret = {}
        ret[ 'block_start' ] = SwfBlockStart
        ret[ 'tag'         ] = SwfTag
        ret[ 'block_len'   ] = BlockLen
        ret[ 'id'          ] = self.le2Byte(self.swfRead(2))
        ret[ 'alpha'       ] = self.swfRead(4)
        ret[ 'value'       ] = self.swfBlockMisc(BlockLen - 6)
        self.Block = ret
        return True

    #-----------------------------------
    # ブロックバイナリデータ格納
    def swfBlockMisc(self, BlockLen):
        if BlockLen:
            return self.swfRead(BlockLen)
        else:
            return None

    #-----------------------------------
    def Save(self, OutFile):
        f = open(OutFile, 'wb')
        f.write(self.Block['value'])
        f.close()

    def swfRead(self, Num):
        self.SwfPos += Num
        return self.Swf[self.SwfPos - Num: self.SwfPos]

    def le2Byte(self, s):
        "LittleEndian to 2 Byte"
        return struct.unpack('<H', s)[0]

    def le4Byte(self, s):
        "LittleEndian to 4 Byte"
        return struct.unpack('<L', s)[0]

#-------------------------------------------------------------------------------
class authenticate(threading.Thread):
    _response = {}
    _response['authed' ] = 0
    _response['area_id'] = ''

    def __init__(self):
        threading.Thread.__init__(self)
        self.setDaemon(True)

    #-----------------------------------
    def run(self):
        self.startAppIDAuth()

    #-----------------------------------
    def startAppIDAuth(self):
        _loc_1 = appIDAuth()
        _loc_1.start()

        if _loc_1._response['auth_token'] != "" and _loc_1._response['auth_token'] > 0:
            self._response = _loc_1._response
            self.startChallengeAuth()
        else:
            print 'failed get token'

    #-----------------------------------
    def startChallengeAuth(self):
        _loc_1 = challengeAuth()
        _loc_1.start(self._response)

        if _loc_1._response['area_id'] != "" and _loc_1._response['area_id'] > 0:
            self._response['area_id'] = _loc_1._response['area_id']
            self._response['authed' ] = 1
            #t = threading.Timer(Const.RESUME_TIMER_INTERVAL, self.resumeTimer)
            #t.setDaemon(True)
            #t.start()
            #time.sleep(Const.RESUME_TIMER_INTERVAL)
            #self.resumeTimer()
        else:
            print 'failed get area_id'

    #-----------------------------------
    def resetTimer(self):
        self._response = None
        self.startAppIDAuth()

    #-----------------------------------
    def resumeTimer(self):
        self.startChallengeAuth()
        #if __debug__:print ("Resume Timer\n")
        log("Resume Timer")

#-------------------------------------------------------------------------------
class appIDAuth(Params, object):
    #def __init__(self):
    #    return True

    #-----------------------------------
    def start(self):
        headers = {'pragma': 'no-cache',
            #'X-Radiko-App': 'pc_1',
            #'X-Radiko-App-Version': '2.0.1',
            'X-Radiko-App': 'pc_ts',
            'X-Radiko-App-Version': '4.0.0',
            'X-Radiko-User': 'test-stream',
            'X-Radiko-Device': 'pc'}

        req = urllib2.Request(self.AUTH1_URL, headers=headers, data='\r\n')
        auth1fms = urllib2.urlopen(req).info()

        self._response = {}
        self._response['auth_token'] = auth1fms['X-Radiko-AuthToken']
        self._response['key_offset'] = int(auth1fms['X-Radiko-KeyOffset'])
        self._response['key_length'] = int(auth1fms['X-Radiko-KeyLength'])

        '''if __debug__:
            print ("authtoken: %s\noffset: %d length: %d\n" % ( \
                self._response['auth_token'],
                self._response['key_offset'],
                self._response['key_length']))'''
        log("authtoken: %s, offset: %d, length: %d" % ( \
            self._response['auth_token'],
            self._response['key_offset'],
            self._response['key_length']))

#-------------------------------------------------------------------------------
class challengeAuth(Params, object):
    #def __init__(self):
    #    return True

    #-----------------------------------
    def start(self, _response):
        self._response = _response

        if 'partial_key' not in self._response or self._response['partial_key'] == '':
            self._response['partial_key'] = self.createPartialKey()

        headers = {'pragma': 'no-cache',
            #'X-Radiko-App': 'pc_1',
            #'X-Radiko-App-Version': '2.0.1',
            'X-Radiko-App': 'pc_ts',
            'X-Radiko-App-Version': '4.0.0',
            'X-Radiko-User': 'test-stream',
            'X-Radiko-Device': 'pc',
            'X-Radiko-Authtoken': self._response['auth_token'],
            'X-Radiko-Partialkey': self._response['partial_key']}

        req = urllib2.Request(self.AUTH2_URL, headers=headers, data='\r\n')
        auth2fms = urllib2.urlopen(req).read().decode('utf-8')

        self._response['area_id'] = auth2fms.split(',')[0].strip()
        '''if __debug__:
            print ("authtoken: %s\noffset: %d length: %d \npartialkey: %s\n" % ( \
                self._response['auth_token'],
                self._response['key_offset'],
                self._response['key_length'],
                self._response['partial_key']))'''
        log("authtoken: %s, offset: %d, length: %d, partialkey: %s" % ( \
            self._response['auth_token'],
            self._response['key_offset'],
            self._response['key_length'],
            self._response['partial_key']))

    #-----------------------------------
    def createPartialKey(self):
        f = open(self.KEY_FILE,'rb')
        f.seek(self._response['key_offset'])
        partialkey = b64encode(f.read(self._response['key_length'])).decode('utf-8')
        f.close()
        return partialkey


#-------------------------------------------------------------------------------
class Radiko(Params):

    def __init__(self, area, token, renew=False):
        self.id = 'radiko'
        self.area = area
        self.token = token
        log('area:%s, token:%s' % (self.area,self.token))
        # 放送局データと設定データを初期化
        self.getStationFile(renew)

    def getStationFile(self, renew=False):
        # キャッシュがあれば何もしない
        if renew == False and os.path.isfile(self.STATION_FILE) and os.path.isfile(self.SETTINGS_FILE):
            return
        # キャッシュがなければウェブから読み込む
        url = '%s%s.xml' % (self.STATION_URL ,self.area)
        data = urlread(url)
        # データ変換
        dom = convert(parse(data))
        station = dom['stations'].get('station',[])
        station = station if isinstance(station,list) else [station]
        # 放送局データ
        buf = []
        for index, s in enumerate(station):
            buf.append(
                '<station>'
                '<id>radiko_{id}</id>'
                '<name>{name}</name>'
                '<logo_large>{logo}</logo_large>'
                '<url>{url}</url>'
                '<lag>{lag}</lag>'
                '</station>'
                .format(id=s['id'],
                    name=s['name'],
                    logo=s['logo_large'],
                    url='%s/%s/_definst_/simul-stream.stream live=1 conn=S: conn=S: conn=S: conn=S:%s' % (self.STREAM_URL, s['id'], self.token),
                    lag=self.LAG))
        # 放送局データを書き込む
        with open(self.STATION_FILE, 'w') as f:
            f.write('\n'.join(buf))
        # 設定データ
        buf = []
        for index, s in enumerate(station):
            url = '%s/%s/_definst_/simul-stream.stream live=1 conn=S: conn=S: conn=S: conn=S:%s' % (self.STREAM_URL, id, self.token)
            buf.append(
                '    <setting label="{name}" type="bool" id="radiko_{id}" default="true" enable="eq({offset},2)"/>'
                .format(id=s['id'],
                    name=s['name'],
                    offset=-1-index))
        # 設定データを書き込む
        with open(self.SETTINGS_FILE, 'w') as f:
            f.write('\n'.join(buf))

    def getStationData(self):
        with open(self.STATION_FILE, 'r') as f:
            data = f.read()
        return data

    def getSettingsData(self):
        with open(self.SETTINGS_FILE, 'r') as f:
            data = f.read()
        return data

    def getProgramFile(self):
        try:
            url = '%s?area_id=%s'  % (self.PROGRAM_URL, self.area)
            data = urlread(url, ('Referer', self.REFERER_URL))
        except:
            log('failed')
            return
        with open(self.PROGRAM_FILE, 'w') as f:
            f.write(data)

    def getProgramData(self, renew=False):
        if renew or not os.path.isfile(self.PROGRAM_FILE):
            self.getProgramFile()
        with open(self.PROGRAM_FILE, 'r') as f:
            data = f.read()
        # データ抽出
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
                progs.append(
                    {
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
                    }
                )
            buf.append({'id':'radiko_%s' % s['@id'], 'progs':progs})
        return buf
