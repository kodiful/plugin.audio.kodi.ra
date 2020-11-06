# -*- coding: utf-8 -*-

from const import Const
from common import *
from xmltodict import parse

import os
import sys
import glob
import re
import urllib, urllib2
import datetime, time
import xml.dom.minidom
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

from hashlib import md5
from PIL import Image
from cStringIO import StringIO

from resources.lib.downloads import Downloads
from resources.lib.keywords  import Keywords

class Params:
    # ファイル
    PROGRAM_FILE = os.path.join(Const.DATA_PATH, 'program.json')
    STATION_FILE = os.path.join(Const.DATA_PATH, 'station.json')
    # タイトル標示のテンプレート
    TITLE_KK = '[COLOR khaki]%s %s[/COLOR]'
    TITLE_LG = '[COLOR lightgreen]%s %s[/COLOR]'
    # ビュレットシンボル
    BULLET   = '\xe2\x96\xb6'


class Programs:

    def __init__(self, services=()):
        # インスタンス変数を初期化
        self.services = services
        self.stations = []
        self.programs = []
        self.matched_programs = []
        # データ抽出
        for data in reduce(lambda x,y:x+y, [service.getStationData() for service in self.services], []):
            # ロゴ画像をダウンロード
            logopath = self.__save_logo(data['id'], data.get('logo_large'))
            # 放送局
            s = {
                'id': data['id'],
                'name': data['name'],
                'logo_large': data.get('logo_large',''),
                'url': data.get('url',''),
                'delay': data.get('delay',0),
                'logo_path': logopath,
                'fanart_artist': logopath,
            }
            # 配列に追加
            self.stations.append(s)

    def __save_logo(self, id, url):
        logopath = os.path.join(Const.MEDIA_PATH, 'logo_%s.png' % id)
        if not os.path.isfile(logopath):
            try:
                if url:
                    buffer = urlread(url)
                else:
                    buffer = urlread(Const.LOGO_URL)
            except:
                buffer = urlread(Const.LOGO_URL)
            img = Image.open(StringIO(buffer))
            w = img.size[0]
            h = img.size[1]
            if w > 216:
                h = int(216.0*h/w)
                w = 216
                img = img.resize((216, h), Image.ANTIALIAS)
            background = Image.new('RGB', ( 216, 216 ), (255, 255, 255))
            try:
                background.paste(img, (int((216-w)/2), int((216-h)/2)), img)
            except:
                background.paste(img, (int((216-w)/2), int((216-h)/2)))
            background.save(logopath, 'PNG')
        return logopath

    def setup(self, renew=False):
        # 全番組の配列を初期化
        self.programs = []
        # データ抽出
        for data in reduce(lambda x,y:x+y, [service.getProgramData(renew) for service in self.services]):
            # この放送局の番組の配列を初期化
            s = self.__search_station(data['id'])
            if s is None:
                # 未知の放送局がある場合はキャッシュを削除してリスタート
                log('unknown id:', data['id'], error=True)
                notify('Updating station data...')
                xbmc.executebuiltin('RunPlugin(%s?action=clear)' % (sys.argv[0]))
                return None, None
            # この放送局のDOMからデータを抽出して配列に格納
            buf = []
            for p in data['progs']:
                q = {
                    'id': s['id'],
                    'name': s['name'],
                    'source': s['url'],
                    'delay': s['delay'],
                    'title': p.get('title',''),
                    'ft': p.get('ft',''),
                    'ftl': p.get('ftl',''),
                    'to': p.get('to',''),
                    'tol': p.get('tol',''),
                    'sub_title': p.get('sub_title',''),
                    'pfm': p.get('pfm',''),
                    'desc': p.get('desc',''),
                    'info': p.get('info',''),
                    'url': p.get('url',''),
                    'subtitle': p.get('subtitle',''),
                    'content': p.get('content',''),
                    'act': p.get('act',''),
                    'music': p.get('music',''),
                    'free': p.get('free',''),
                    'description': self.__description(p)
                }
                # 配列に追加
                self.programs.append(q)
                buf.append(q)
            s['programs'] = buf
        # ファイルに書き込む
        write_json(Params.STATION_FILE, self.stations)
        # ダイジェストを返す
        return self.__digest()

    def __search_station(self, id):
        results = filter(lambda s: s['id']==id, self.stations)
        if len(results) == 1:
            return results[0]
        else:
            return None

    def __description(self, p):
        description = []
        for attr in ('sub_title','pfm','desc','info','url','subtitle','content','act','music','free'):
            q = p.get(attr)
            if q: description.append('&lt;div title=&quot;{attr}&quot;&gt;{content}&lt;/div&gt;'.format(attr=attr, content=q))
        return ' '.join(description)

    def __showhide(self, id):
        category = id.split('_')[0]
        try:
            if Const.GET(category) == '0': return True
            if Const.GET(category) == '1': return False
            if Const.GET(id) == 'true': return True
            if Const.GET(id) == 'false': return False
        except:
            pass
        return True

    def __digest(self):
        # 開始/終了時刻が定義された番組を抽出
        p = filter(lambda x:x['ft'] and x['to'], self.programs)
        # 開始/終了時刻のペアから現在の番組情報のハッシュを生成
        data = reduce(lambda x,y:x+y, map(lambda x:x['ft']+x['to'], p))
        hash = md5(data).hexdigest()
        # 終了済みの番組は現在時刻を、それ以外は開始時刻を抽出
        now = nexttime()
        p = map(lambda x:now if x['to']<now else x['ft'], p)
        # 現在時刻以降の時刻を抽出
        p = filter(lambda t: t>=now, p)
        # 直近の時刻を抽出
        nextaired = min(p) if p else '99999999999999'
        return nextaired, hash

    def show(self):
        # ファイルから読み込む
        self.stations = read_json(Params.STATION_FILE)
        # 放送局表示
        for s in filter(lambda x:self.__showhide(x['id']), self.stations):
            title = '[COLOR white]%s[/COLOR]' % s['name']
            if len(s['programs']) == 0:
                title += ' ' + Params.TITLE_KK % (Params.BULLET,Const.STR(30058))
            else:
                for i, p in enumerate(s['programs']):
                    title1 = p['title']
                    if p['ftl'] and p['tol']: title1 = '%s (%s:%s～%s:%s)' % (p['title'],p['ftl'][0:2],p['ftl'][2:4],p['tol'][0:2],p['tol'][2:4])
                    if i==0: title += ' ' + Params.TITLE_KK % (Params.BULLET,title1)
                    if i>0:  title += ' ' + Params.TITLE_LG % (Params.BULLET,title1)
            # リストアイテムを定義
            li = xbmcgui.ListItem(title, iconImage=s['fanart_artist'], thumbnailImage=s['fanart_artist'])
            # type='misic' crashes when rtmpe stream being played
            li.setInfo(type='video', infoLabels={'title':s['name']})
            # コンテクストメニュー
            contextmenu = []
            # 番組情報を更新
            contextmenu.append((Const.STR(30055), 'Container.Update(%s?action=showPrograms,replace)' % (sys.argv[0])))
            # ダウンロード設定
            if Const.GET('download') == 'true':
                for i, p in enumerate(s['programs']):
                    if p['ft'].isdigit() and p['to'].isdigit():
                        # 保存
                        if i==0: menu = Params.TITLE_KK % (Const.STR(30056),p['title'])
                        if i>0:  menu = Params.TITLE_LG % (Const.STR(30056),p['title'])
                        contextmenu.append((menu, 'RunPlugin({url}?action=addDownload&{query})'.format(url=sys.argv[0], query=urllib.urlencode(p))))
                        # キーワード追加
                        if i==0: menu = Params.TITLE_KK % (Const.STR(30057),p['title'])
                        if i>0:  menu = Params.TITLE_LG % (Const.STR(30057),p['title'])
                        contextmenu.append((menu, 'RunPlugin({url}?action=addKeyword&{query})'.format(url=sys.argv[0], query=urllib.urlencode(p))))
            # ラジオ設定
            if s['id'].find('misc_') == 0:
                # 変更
                contextmenu.append((Const.STR(30319), 'RunPlugin(%s?action=beginEditStation&id=%s)' % (sys.argv[0],s['id'])))
                # 削除
                contextmenu.append((Const.STR(30318), 'RunPlugin(%s?action=deleteStation&id=%s)' % (sys.argv[0],s['id'])))
            # アドオン設定
            contextmenu.append((Const.STR(30051), 'RunPlugin(%s?action=settings)' % (sys.argv[0])))
            # コンテクストメニュー設定
            li.addContextMenuItems(contextmenu, replaceItems=True)
            # リストアイテムを追加
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), s['url'], listitem=li, isFolder=False)
        # リストアイテム追加完了
        xbmcplugin.endOfDirectory(int(sys.argv[1]), succeeded=True)

    def match(self):
        self.matched_programs = []
        keywords = Keywords()
        # 開始時間、終了時間が規定されている番組について
        for p in filter(lambda p: p['ft'] and p['to'], self.programs):
            # キーワードと照合
            k = keywords.match(p)
            if k:
                status = Downloads().status(p['id'],p['ft'])
                if status == 0:
                    self.matched_programs.append({'program':p, 'keyword':k})
                    log('program matched. id:{id}, start:{start}, title:{title}, keyword:{keyword}'.format(
                        id = p['id'],
                        start = p['ft'],
                        title = p['title'],
                        keyword = k['key']))
                elif status > 1:
                    log('inconsistency found ({status}). id:{id}, start:{start}, title:{title}, keyword:{keyword}'.format(
                        id = p['id'],
                        start = p['ft'],
                        title = p['title'],
                        keyword = k['key'],
                        status = status))

    def download(self):
        now = datetime.datetime.now()
        for m in self.matched_programs:
            p = m['program']
            k = m['keyword']
            # 開始直前であれば保存処理を開始
            start = strptime(p['ft'], '%Y%m%d%H%M%S')
            wait = start - now
            if wait.days == 0 and wait.seconds < Const.PREP_INTERVAL:
                status = Downloads().add(
                    id=p['id'],
                    name=p['name'],
                    ft=p['ft'],
                    to=p['to'],
                    title=p['title'],
                    description=p['description'],
                    source=p['source'],
                    delay=p['delay'],
                    key=k['key'])
                if status is None:
                    log('download scheduled. id:{id}, start:{start}, title:{title}, keyword:{keyword}'.format(
                        id = p['id'],
                        start = p['ft'],
                        title = p['title'],
                        keyword = k['key']))
                else:
                    log('scheduling failed ({status}). id:{id}, start:{start}, title:{title}, keyword:{keyword}'.format(
                        id = p['id'],
                        start = p['ft'],
                        title = p['title'],
                        keyword = k['key'],
                        status = status))
