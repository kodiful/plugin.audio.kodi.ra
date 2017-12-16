# -*- coding: utf-8 -*-

# radikoのプレーヤ(player.swf)をダウンロード
# player.swfに潜むRadikoPlayer_keyImageを抽出
# https://radiko.jp/v2/api/auth1_fmsへPOSTでアクセスしてauthtokenとKeyLength、KeyOffsetを取得
# KeyLength、KeyOffsetを基にRadikoPlayer_keyImageからバイナリデータを取得しBASE64で符号化(PartialKey)
# authtokenとPartialKeyをリクエストヘッダに載せてhttps://radiko.jp/v2/api/auth2_fmsへPOSTでアクセス
# 認証に成功すればauthtokenを使ってrtmpdumpでデータを受信

# cf. http://d.hatena.ne.jp/zariganitosh/20130124/rtmpdump_radiko_access

import resources.lib.common as common
from common import(log,notify)

import os
import struct
import zlib
import urllib, urllib2
import xml.dom.minidom
import threading, time
import codecs
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

from base64 import b64encode
from math import ceil

__radiko_path__ = os.path.join(common.data_path, 'radiko')
if not os.path.isdir(__radiko_path__): os.makedirs(__radiko_path__)

__key_file__      = os.path.join(__radiko_path__, 'authkey.dat')
__player_file__   = os.path.join(__radiko_path__, 'player.swf')

__program_file__  = os.path.join(__radiko_path__, 'program.xml')
__station_file__  = os.path.join(__radiko_path__, 'station.xml')
__settings_file__ = os.path.join(__radiko_path__, 'settings.xml')

__auth1_url__     = 'https://radiko.jp/v2/api/auth1_fms'
__auth2_url__     = 'https://radiko.jp/v2/api/auth2_fms'
#__player_url__    = 'http://radiko.jp/player/swf/player_3.0.0.01.swf'
__player_url__    = 'http://radiko.jp/apps/js/flash/myplayer-release.swf'
__station_url__   = 'http://radiko.jp/v2/station/list/'
__referer_url__   = 'http://radiko.jp/player/timetable.html'
__program_url__   = 'http://radiko.jp/v2/api/program/now'
__stream_url__    = 'rtmpe://f-radiko.smartstream.ne.jp'

__lag__           = 20

__object_tag__    = 87
#__object_id__     = 14
__object_id__     = 12


#-------------------------------------------------------------------------------
class getAuthkey(object):

    def __init__(self):

        while True:
            try:
                response = urllib2.urlopen(__player_url__)
                UrlSize = int(response.headers["content-length"])
            except : UrlSize = 0

            if os.path.exists(__player_file__) : PathSize = int(os.path.getsize(__player_file__))
            else : PathSize = 0

            if UrlSize > 0 and UrlSize != PathSize:
                if os.path.exists(__player_file__) : os.remove(__player_file__)
                if os.path.exists(__key_file__) : os.remove(__key_file__)
                open(__player_file__, 'wb').write(response.read())
                self.keyFileDump()

            elif not os.path.exists(__key_file__) and PathSize > 0 :
                self.keyFileDump()

            if os.path.exists(__key_file__) : break
            else : time.sleep(1)

    #-----------------------------------
    def keyFileDump(self):
        tmpSwf = open(__player_file__, 'rb').read()
        self.Swf = tmpSwf[:8] + zlib.decompress(tmpSwf[8:]) # 読み込んだswfバッファ
        self.SwfPos = 0 # swf読み込みポインタ

        self.parseSwfHead()
        self.output_file = __key_file__
        while self.swfBlock(): # タブブロックがある限り
            #if __debug__: print (self.Block['tag'], self.Block['block_len'], self.Block['id'])
            log(self.Block['tag'], self.Block['block_len'], self.Block['id'])

            if self.Block['tag'] == __object_tag__ and self.Block['id'] == __object_id__:
                self.Save(__key_file__)
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
            #t = threading.Timer(common.resume_timer_interval, self.resumeTimer)
            #t.setDaemon(True)
            #t.start()
            #time.sleep(common.resume_timer_interval)
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
class appIDAuth(object):
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

        req = urllib2.Request(__auth1_url__, headers=headers, data='\r\n')
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
class challengeAuth(object):
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

        req = urllib2.Request(__auth2_url__, headers=headers, data='\r\n')
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
        f = open(__key_file__,'rb')
        f.seek(self._response['key_offset'])
        partialkey = b64encode(f.read(self._response['key_length'])).decode('utf-8')
        f.close()
        return partialkey


#-------------------------------------------------------------------------------
class Radiko:

    def __init__(self, area, token, renew=False):
        self.id = 'radiko'
        self.area = area
        self.token = token
        log('area:%s, token:%s' % (self.area,self.token))
        # 放送局データと設定データを初期化
        self.getStationFile(renew)

    def getStationFile(self, renew=False):
        # キャッシュがあれば何もしない
        if renew == False and os.path.isfile(__station_file__) and os.path.isfile(__settings_file__):
            return
        # キャッシュがなければウェブから読み込む
        url = '%s%s.xml' % (__station_url__ ,self.area)
        response = urllib.urlopen(url)
        data = response.read()
        response.close()
        # データ変換
        dom = xml.dom.minidom.parseString(data)
        results = []
        settings = []
        i = -1
        stations = dom.getElementsByTagName('station')
        for station in stations:
            id = station.getElementsByTagName('id')[0].firstChild.data
            name = station.getElementsByTagName('name')[0].firstChild.data
            logo = station.getElementsByTagName('logo_large')[0].firstChild.data
            url = '%s/%s/_definst_/simul-stream.stream live=1 conn=S: conn=S: conn=S: conn=S:%s' % (__stream_url__,id,self.token)
            options = '-r "%s/%s/_definst_/simul-stream.stream" -C S: -C S: -C S: -C S:%s -v' % (__stream_url__,id,self.token)
            # pack as xml
            xmlstr = '<station>'
            xmlstr += '<id>radiko_%s</id>' % (id)
            xmlstr += '<name>%s</name>' % (name)
            xmlstr += '<logo_large>%s</logo_large>' % (logo)
            xmlstr += '<url>%s</url>' % (url)
            xmlstr += '<options>%s</options>' % (options)
            xmlstr += '<lag>%d</lag>' % (__lag__)
            xmlstr += '</station>'
            results.append(xmlstr)
            # pack as xml (for settings)
            xmlstr = '    <setting label="%s" type="bool" id="radiko_%s" default="false" enable="eq(%d,2)"/>' % (name,id,i)
            settings.append(xmlstr)
            i = i-1
        # 放送局データを書き込む
        f = codecs.open(__station_file__,'w','utf-8')
        f.write('\n'.join(results))
        f.close()
        # 設定データを書き込む
        f = codecs.open(__settings_file__,'w','utf-8')
        f.write('\n'.join(settings))
        f.close()

    def getStationData(self):
        f = codecs.open(__station_file__,'r','utf-8')
        data = f.read()
        f.close()
        return data

    def getSettingsData(self):
        f = codecs.open(__settings_file__,'r','utf-8')
        data = f.read()
        f.close()
        return data

    def getProgramFile(self):
        try:
            url = '%s?area_id=%s'  % (__program_url__,self.area)
            opener = urllib2.build_opener()
            opener.addheaders = [('Referer', __referer_url__)]
            response = opener.open(url)
            data = response.read()
            response.close()
        except:
            log('failed')
            return
        f = codecs.open(__program_file__,'w','utf-8')
        f.write(data.decode('utf-8'))
        f.close()

    def getProgramData(self, renew=False):
        if renew or not os.path.isfile(__program_file__):
            self.getProgramFile()
        xmlstr = open(__program_file__, 'r').read()
        dom = xml.dom.minidom.parseString(xmlstr)
        results = []
        stations = dom.getElementsByTagName('station')
        for station in stations:
            id = station.getAttribute('id')
            station.setAttribute('id', 'radiko_%s' % id)
            xmlstr = station.toxml('utf-8').decode('utf-8')
            results.append(xmlstr)
        return '\n'.join(results)
