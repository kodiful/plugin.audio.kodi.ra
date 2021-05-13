# -*- coding: utf-8 -*-

from resources.lib.const import Const
from resources.lib.common import log
from resources.lib.common import timestamp
from resources.lib.common import urlread
from resources.lib.common import read_file
from resources.lib.common import read_json
from resources.lib.common import write_file

from xmltodict import parse

import os
import urllib
import json
from datetime import datetime, timedelta, timezone


class Params:
    # ファイルパス
    DATA_PATH = os.path.join(Const.DATA_PATH, 'jcba')
    if not os.path.isdir(DATA_PATH):
        os.makedirs(DATA_PATH)
    # ファイル
    STATION_FILE = os.path.join(Const.TEMPLATE_PATH, 'cp', 'community', 'station_sj.json') # 放送局データ "Calendar"項を追加してます
    NEXTUPDT_FILE = os.path.join(DATA_PATH, 'nextupdt.json')
    # URL
    PROGRAM_URL = 'https://content.googleapis.com/calendar/v3/calendars/%s/events'

    STN = 'jcba_' # who i am?


class Jcba(Params):

    def __init__(self, renew=False):
        return

    def setup(self, renew=False):
        # 放送局データを取得、設定ダイアログを書き出す
        return

    def getStationData(self): # Common(Programs)
        # 放送局データを読み込む
        if not os.path.isfile(self.STATION_FILE):
            self.setup()
        #return read_json(self.STATION_FILE)

        sd = read_json(self.STATION_FILE)
        if self.STN:
            ids = self.getActiveStation(self.STN)
            if ids:
                ss = []
                for id in ids:
                    s = [s for s in sd if s['id']==id['id']]
                    if s:
                        ss.append({
                            'id': s[0]['id'],
                            'calendar': s[0].get('calendar',''),
                            'logo_large': s[0].get('logo_large',''),
                            'name': s[0].get('name',''),
                            'onair': s[0].get('onair',''),
                            'stream': s[0].get('stream',''),
                            'url': s[0].get('url','')
                        })
                sd = ss
        return sd

    def getSettingsData(self): # common
        # 設定ダイアログを読み込む
        if not os.path.isfile(self.SETTINGS_FILE):
            self.setup()
        return read_file(self.SETTINGS_FILE)

    def getSettingsData2(self, fn = ''): # CommunityRadio(jcba/listenradio/simulradio)
        # 設定ダイアログを読み込む
        fn = os.path.join(Const.TEMPLATE_PATH, 'cp', 'community', fn)
        if not os.path.isfile(fn):
            self.setup()
        return read_file(fn)

    def getActiveStation(self, stn=''):
        # JCBA/ListenRadionにて，聴取する局を抽出します。
        ret = None
        data = read_file(Const.USERSETTINGS_FILE) # /⁨addon_data⁩/⁨plugin.audio.kodi.ra⁩/settings.xml
        if data:
            dom = parse(data)
            st = dom['settings']['setting']
            ret = [{'id': s.get('@id')} for s in st if s.get('@id')[0:5] == stn and s.get('#text') == 'true'] # 聴取対象局リスト
        return ret

    def chkScheduleExpiration(self, fp=''):
        ret = False
        data = ''
        data = read_file(fp)
        if data:
            sj = json.loads(data)
            items = sj['items']
            # log('no of items?: %s' % len(items))
            if len(items) <= 3:
                ret = True
            else:
                now = datetime.now()
                # log('%s' % items[len(items)-3]['end']['dateTime'][0:19])
                if  now < datetime.strptime(items[len(items)-3]['end']['dateTime'][0:19], '%Y-%m-%dT%H:%M:%S'):
                    ret = True

        # log('result: %s' % ret)
        return ret

    def getSchedule(self, calendar='', fp=''):
        url = ''
        params = {}
        headers = {}
        url = (self.PROGRAM_URL % urllib.parse.quote(calendar))
        # log('target url:%s' % url)

        params = {
            'orderBy':'startTime',
            'timeMin':datetime.strftime(datetime.now(timezone.utc),'%Y-%m-%dT%H:%M:%SZ'),
            'timeMax':datetime.strftime(datetime.now(timezone.utc)+timedelta(days=1),'%Y-%m-%dT%H:%M:%SZ'),
            'timeZone':'Asia/Tokyo',
            'maxResults':'24', # >='3'
            'singleEvents':'true',
            'fields':'description,items(anyoneCanAddSelf,attendees,attendeesOmitted,colorId,description,end,endTimeUnspecified,id,source,start,status,summary,description),summary',
            'key':'AIzaSyAWUXnG9xZJSHfDXRBTMq5uxBVUBEUXWeU'
        }
        # log('target params:%s' % params)

        headers = {
            'x-referer': 'https://www.jcbasimul.com', 
            'referer': 'https://content.googleapis.com/static/proxy.html?usegapi=1&jsh=m%3B%2F_%2Fscs%2Fapps-static%2F_%2Fjs%2Fk%3Doz.gapi.ja.H6QrK-xKX2c.O%2Fam%3DAQ%2Fd%3D1%2Fct%3Dzgms%2Frs%3DAGLTcCP5KUdrvNMBxQCtLtkegDcOaSTRPw%2Fm%3D__features__'
        }
        # log('target headers:%s' % headers)

        try:
            if calendar:
                data = urlread(url, headers, params)
                write_file(fp, data)
            else:
                raise urllib.error.URLError
        except Exception:
            write_file(fp, '')
            log('failed to get data from url:%s' % url)

    def getProgramData(self, renew=False):
        # キャッシュ(cache/data/jcba以下)を確認 ->番組表.json取得
        # jcbaの番組表は，「”NowOnAir”から，それ以降 n番組分を取得する」って感じ（先n日分じゃない）
        # 通常(WebUIでは)，3番組を取得，番組が変わる度に再取得が行われる… 様だ。

        # 最新の番組データを取得、なければ放送局データから生成する
        results = [{'id': s['id'], 'progs': [{'title': s.get('onair') or Const.STR(30059)}]} for s in self.getStationData()]
        nextupdate = '0' * 14
        #if Const.GET( "jcbaschedule" ) == '0':
        if Const.GET( "commschedule" ) == '0':
            nextupdate = '9' * 14
            return results, nextupdate

        # ここから
        data = '' # read_file
        ids = [] # @id list
        buf = []

        ids = self.getActiveStation(self.STN)
        if ids:
            sd = self.getStationData()
            for id in ids:
                ss = []
                ss = [s for s in sd if s['id']==id['id']]

                fp = os.path.join(self.DATA_PATH, ss[0]['id']+'_Schedule.json')
                if ss[0]['calendar']:
                    c = ss[0]['calendar']
                    if not os.path.isfile(fp): # ファイルが無ければ取得。
                        self.getSchedule(c, fp)
                    elif self.chkScheduleExpiration(fp) == False: # 賞味期限切れの場合，取得。
                        self.getSchedule(c, fp)
                else:
                    log('no calendar info %s, make vacant file ' % id['id'])
                    write_file(fp, '') # 空ファイル生成

                # 番組情報抽出，書き込み
                data = '' # read_file
                progs = []
                pp = []
                
                data = read_file(fp)
                if data:
                    sj = json.loads(data)
                    items = sj['items']
                    now = datetime.now()

                    idx = 0
                    for s in items:
                        idx += 1
                        if datetime.strptime(s['start']['dateTime'][0:19], '%Y-%m-%dT%H:%M:%S') < now < datetime.strptime(s['end']['dateTime'][0:19], '%Y-%m-%dT%H:%M:%S'):
                            pp = [s]
                            break
                    pp.append(items[idx])
                    # log('pp: %s' % pp)

                    for p in pp:
                        t = p['start']['dateTime']
                        ft = str(t[0:4]) + str(t[5:7]) + str(t[8:10]) + str(t[11:13]) + str(t[14:16]) + str(t[17:19])
                        ftl = str(t[11:13]) + str(t[14:16])
                        t = p['end']['dateTime']
                        to = str(t[0:4]) + str(t[5:7]) + str(t[8:10]) + str(t[11:13]) + str(t[14:16]) + str(t[17:19])
                        tol = str(t[11:13]) + str(t[14:16])
                        progs.append({
                            'ft': ft,
                            'ftl': ftl,
                            'to': to,
                            'tol': tol,
                            'title': p.get('summary', 'n/a'),
                            'subtitle': p.get('sub_title', ''),
                            'pfm': p.get('pfm', ''),
                            'desc': p.get('ProgramSummary', ''),
                            'info': p.get('ProgramSummary', ''),
                            'url': p.get('url', ''),
                            'content': p.get('content', ''),
                            'act': p.get('act', ''),
                            'music': p.get('music', ''),
                            'free': p.get('free', '')
                        })
                        results.append({'id': '%s' % id['id'], 'progs': progs})
                        buf += progs
            # 次の更新時刻
            nextupdate = self.getNextUpdate(buf)
        # 次の更新時刻をファイルに書き込む
        d = read_file(self.NEXTUPDT_FILE)
        if d:
            if d < timestamp() or nextupdate < d:
                write_file(self.NEXTUPDT_FILE, nextupdate)
        else:
            write_file(self.NEXTUPDT_FILE, nextupdate)
        return results, nextupdate # 'nextupdate'は，表示している番組情報の更新タイミング

    def getNextUpdate(self, qbuf): # common
        # 現在時刻
        now = timestamp()
        # 開始/終了時刻が定義された番組を抽出
        p = list(filter(lambda x: x['ft'] and x['to'], qbuf))
        # 終了済みの番組は現在時刻を、それ以外は開始時刻を抽出
        p = list(map(lambda x: now if x['to'] < now else x['ft'], p))
        # 現在時刻以降の時刻を抽出
        p = list(filter(lambda t: t >= now, p))
        # 直近の時刻を抽出
        return min(p) if p else now
