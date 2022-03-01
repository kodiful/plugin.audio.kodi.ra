# -*- coding: utf-8 -*-

from resources.lib.cp.jcba import Jcba

from resources.lib.const import Const
from resources.lib.common import log
from resources.lib.common import timestamp
from resources.lib.common import urlread
from resources.lib.common import read_file
from resources.lib.common import write_file

from xmltodict import parse

import os
import sys
import json
from datetime import datetime, timedelta

import xbmc


class Params:
    # ファイルパス
    DATA_PATH = os.path.join(Const.DATA_PATH, 'listenradio')
    if not os.path.isdir(DATA_PATH):
        os.makedirs(DATA_PATH)
    # ファイル
    STATION_FILE = os.path.join(Const.TEMPLATE_PATH, 'cp', 'community', 'station_lr.json') # 放送局データ
    NEXTUPDT_FILE = os.path.join(DATA_PATH, 'nextupdt.json')
    # URL
    STATION_URL='http://listenradio.jp/service/categorychannel.aspx?categoryid=99999' # 全局リスト →取ってきてから欲しい分だけ抽出する？
    PROGRAM_URL='http://listenradio.jp/service/Schedule.aspx?channelId=%s'            # 番組表(1週間分)

    STN = 'lisr_' # who i am?


class Listenradio(Params, Jcba):

    def __init__(self, renew=False):
        return

    def setup(self, renew=False):
        # 放送局データを取得、設定ダイアログを書き出す
        return

    def chkScheduleExpiration(self, fp=''):
        ret = False
        s = ''
        s = read_file(fp)
        if s is not None:
            sj = json.loads(s)
            st = sj['ServerTime'] # "ServerTime":"2021-04-06T17:43:45.9233135+09:00"
            ft = datetime.strptime(str(st[0:19]), '%Y-%m-%dT%H:%M:%S') + timedelta(days=6) # 取り置き済み番組表 賞味期限(6日)
            t = datetime.strptime(timestamp(), '%Y%m%d%H%M%S')
            if t < ft:
                ret = True
        else:
            ret = True

        return ret
    
    def getSchedule(self, id = '', fp = ''):
        url = ''
        try:
            url = (self.PROGRAM_URL % str(id))
            if id:
                data = urlread(url)
                write_file(fp, data)
            else:
                raise urllib.error.URLError
        except Exception:
            write_file(fp, '')
            log('failed to get data from url:%s' % url)

    def getProgramData(self, renew = False):
        # キャッシュ(cache/data/listenradio以下)を確認 ->番組表.json取得
        # listenradioの番組表は，「”NowOnAir”を含む日から，1週間分取得する」って感じ
        # 通常(WebUIでは)，切り替えならが3日分を表示，”NowOnAir”だけは，番組が変わる度に再取得が行われる… 様だ。

        # 最新の番組データを取得、なければ放送局データから生成する
        results = [{'id': s['id'], 'progs': [{'title': s.get('onair') or Const.STR(30059)}]} for s in self.getStationData()]
        nextupdate = '0' * 14
        #if Const.GET( "lisrschedule" ) == '0':
        if Const.GET( "commschedule" ) == '0':
            nextupdate = '9' * 14
            return results, nextupdate

        data = '' # read_file
        ids = []  # @id list

        # キャッシュ(cache/data/listenradio以下)を確認後，番組表.json取得
        ids = self.getActiveStation(self.STN)
        if ids:
            for id in ids:
                fp = os.path.join(self.DATA_PATH, id['id'] + '_Schedule.json')
                if not os.path.isfile(fp):
                    # ファイルが無ければ取得。
                    self.getSchedule(id['id'][5:10], fp)
                elif os.path.getsize(fp) < 10000:
                    # 取得不全(10KB以下は有り得ない)の場合，再取得。
                    # 注意: サーバとやり取りとしては成功しているが，半日分しか取得出来ない場合がある。
                    self.getSchedule(id['id'][5:10], fp)
                elif self.chkScheduleExpiration(fp) == False:
                    # 賞味期限切れの場合，取得。
                    self.getSchedule(id['id'][5:10], fp)

                # *_Schedule.jsonから番組情報を取り出す
                data = ''
                buf = []
                data = read_file(fp)
                if data is not None:
                    data = json.loads(data)
                    dd = data["ProgramSchedule"]

                    progs = []
                    pp = []
                    now = timestamp()

                    pp = [d for d in dd if (d['StartDate']+"00") < now < (d['EndDate']+"00")]
                    psid = pp[0].get('ProgramScheduleId') + 1 # int
                    x = [d for d in dd if d['ProgramScheduleId'] == psid]
                    pp.append(x[0])

                    for p in pp:
                        ft = p.get('StartDate') + "00"
                        ftl = str(ft[8:12])
                        to = p.get('EndDate') + "00"
                        tol = str(to[8:12])
                        progs.append({
                            'ft': ft,
                            'ftl': ftl,
                            'to': to,
                            'tol': tol,
                            'title': p.get('ProgramName', 'n/a'),
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
        return results, nextupdate
