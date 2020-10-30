# -*- coding: utf-8 -*-

from const import Const
from common import *
from xmltodict import parse

import os, sys, glob
import re
import urllib, urllib2
import json
import datetime, time
import xml.dom.minidom
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

from hashlib import md5
from PIL import Image
from cStringIO import StringIO

from resources.lib.downloads import(Downloads)
from resources.lib.keywords  import(Keywords)

def check(id):
    category = id.split('_')[0]
    try:
        if Const.GET(category) == '0': return True
        if Const.GET(category) == '1': return False
        if Const.GET(id) == 'true': return True
        if Const.GET(id) == 'false': return False
    except:
        pass
    return True

class Data:

    def __init__(self, services):
        # インスタンス変数を初期化
        self.stations = []
        self.programs = []
        self.matched_programs = []
        # 放送局データ生成
        self.services = services
        station = reduce(lambda x,y:x+y, [service.getStationData() for service in self.services])
        # データ抽出
        for s in station:
            # ロゴ画像をダウンロード
            logopath = self.__save_logo(s['id'], s['logo_large'])
            # 放送局
            r = {
                'id': s['id'],
                'name': s['name'],
                'logo_large': s.get('logo_large',''),
                'url': s.get('url',''),
                'lag': s.get('lag',0),
                'logo_path': logopath,
                'fanart_artist': logopath,
            }
            # リスト、辞書に保存
            self.stations.append(r)

    def __search_station(self, id):
        results = filter(lambda s: s['id']==id, self.stations)
        if len(results) == 1:
            return results[0]
        else:
            return None

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

    def setPrograms(self, renew=False):
        # 全番組の配列を初期化
        self.programs = []
        # 番組データのDOM生成
        station = reduce(lambda x,y:x+y, [service.getProgramData(renew) for service in self.services])
        # データ抽出
        for s in station:
            # この放送局の番組の配列を初期化
            r = self.__search_station(s['id'])
            if r is None:
                # 未知の放送局がある場合はデータキャッシュを削除してリスタート
                notify('Updating station data...')
                xbmc.executebuiltin('RunPlugin(%s?action=reset)' % (sys.argv[0]))
                return
            # この放送局のDOMからデータを抽出して配列に格納
            buf = []
            for p in s['progs']:
                q = {
                    'id': s['id'],
                    'name': r['name'],
                    'source': r['url'],
                    'lag': r['lag'],
                    'title': p.get('title',''),
                }
                # ft,to,ftl,tol
                for attr in ('ft','to','ftl','tol'):
                    q[attr] = p.get('@'+attr,'')
                # description
                description = []
                for attr in ('sub_title','pfm','desc','info','url','subtitle','content','act','music','free'):
                    q[attr] = p.get(attr,'')
                    if q[attr]:
                        description.append('&lt;div title=&quot;{attr}&quot;&gt;{content}&lt;/div&gt;'.format(attr=attr, content=q[attr]))
                q['description'] = ''.join(description)
                # 配列に追加
                buf.append(q)
                self.programs.append(q)
            r['programs'] = buf

    def onChanged(self):
        self.matched_programs = []
        for p in self.programs:
            # 開始時間、終了時間が規定されている番組について
            if p['ft'] and p['to']:
                # キーワードをチェック
                search = Keywords().search
                for s in search:
                    # キーワードを照合
                    if s['key']:
                        if p['title'].find(s['key']) > -1:
                            pass
                        elif s['s'] == '1' and p['description'].find(s['key']) > -1:
                            pass
                        else:
                            continue
                    else:
                        continue
                    # 曜日を照合
                    if s['day'] == '0':
                        pass
                    elif int(strptime(p['ft'],'%Y%m%d%H%M%S').strftime('%w')) == int(s['day'])-1:
                        pass
                    else:
                        continue
                    # 放送局を照合
                    if s['ch'] == Const.STR(30520):
                        pass
                    elif s['ch'] == p['name']:
                        pass
                    else:
                        continue
                    # 保存済み番組名と照合
                    if s['duplicate'] == '1':
                        skip = False
                        for file in glob.glob(os.path.join(Const.DOWNLOAD_PATH, '*.js')):
                            js_file = os.path.join(Const.DOWNLOAD_PATH, file)
                            mp3_file = os.path.join(Const.DOWNLOAD_PATH, file.replace('.js','.mp3'))
                            if os.path.isfile(js_file) and os.path.isfile(mp3_file):
                                program = read_json(js_file)['program'][0]
                                if p['name'] == program['bc']:
                                    if s['s'] == '0' and p['title'] == program['title']:
                                        # 番組名が一致する
                                        skip = True
                                        break
                                    if s['s'] == '1' and p['title'] == program['title'] and p['description'] == program['description']:
                                        # 番組名と詳細情報が一致する
                                        skip = True
                                        break
                        if skip: continue
                    # とりあえず追加
                    start = strptime(p['ft'],'%Y%m%d%H%M%S')
                    self.matched_programs.append({'program':p, 'start':start, 'key':s['key']})
                    log('start=',start,' name=',p['name'],' title=',p['title'])
                    break

    def onWatched(self):
        now = datetime.datetime.now()
        for m in self.matched_programs:
            # 開始直前であれば保存処理を開始
            wait = m['start'] - now
            if wait.days == 0 and wait.seconds < Const.PREP_INTERVAL:
                p = m['program']
                status = Downloads().add(
                    id=p['id'],
                    name=p['name'],
                    start=p['ft'],
                    end=p['to'],
                    title=p['title'],
                    description=p['description'],
                    source=p['source'],
                    lag=p['lag'],
                    key=m['key'])
                if status:
                    pass
                else:
                    log('start=',strptime(p['ft'],'%Y%m%d%H%M%S'),' name=',p['name'],' title=',p['title'])

    def showPrograms(self):
        # 放送局表示
        for s in self.stations:
            id = s['id']
            if check(id):
                try:
                    programs = s['programs']
                except KeyError:
                    # 既存の放送局がない場合はデータキャッシュを削除してリスタート
                    notify('Updating station data...')
                    xbmc.executebuiltin('RunPlugin(%s?action=reset)' % (sys.argv[0]))
                title = '[COLOR white]%s[/COLOR]' % (s['name'])
                bullet = '\xe2\x96\xb6'
                if len(programs) == 0:
                    title += ' [COLOR khaki]%s %s[/COLOR]' % (bullet,Const.STR(30058))
                    title0 = Const.STR(30058)
                    comment0 = ''
                else:
                    for i in range(len(programs)):
                        p = programs[i]
                        if p['ftl'] == '':
                            title1 = '%s' % (p['title'])
                        else:
                            title1 = '%s (%s:%s～%s:%s)' % (p['title'],p['ftl'][0:2],p['ftl'][2:4],p['tol'][0:2],p['tol'][2:4])
                        if title1:
                            if i==0: title += ' [COLOR khaki]%s %s[/COLOR]' % (bullet,title1)
                            if i>0: title += ' [COLOR lightgreen]%s %s[/COLOR]' % (bullet,title1)
                    title0 = programs[0]['title']
                    comment0 = re.sub(r'&lt;.*?&gt;','',programs[0]['description'])
                # リストアイテムを定義
                li = xbmcgui.ListItem(title, iconImage=s['fanart_artist'], thumbnailImage=s['fanart_artist'])
                #li.setInfo(type='music', infoLabels={'title':title0,'artist':s['name'],'comment':comment0})
                li.setInfo(type='video', infoLabels={'title':s['name'] or s['name']})
                # コンテクストメニュー
                contextmenu = []
                # 番組情報を更新
                contextmenu.append((Const.STR(30055), 'Container.Update(%s?action=showPrograms,replace)' % (sys.argv[0])))
                # 保存、設定
                if Const.GET('download') == 'true':
                    for i in range(len(programs)):
                        p = programs[i]
                        if p['ft'].isdigit() and p['to'].isdigit():
                            # 保存
                            if i==0: menu = '[COLOR khaki]%s%s[/COLOR]' % (Const.STR(30056),p['title'])
                            if i>0: menu = '[COLOR lightgreen]%s%s[/COLOR]' % (Const.STR(30056),p['title'])
                            contextmenu.append((menu,
                                'RunPlugin({url}?action=addDownload&id={id}&name={name}&start={start}&end={end}&title={title}&description={description}&source={source}&lag={lag})'.format(
                                    url=sys.argv[0],
                                    id=id,
                                    name=urllib.quote_plus(s['name'].encode('utf-8')),
                                    start=p['ft'],
                                    end=p['to'],
                                    title=urllib.quote_plus(p['title'].encode('utf-8')),
                                    description=urllib.quote_plus(p['description'].encode('utf-8')),
                                    source=urllib.quote_plus(s['url']),
                                    lag=s['lag']
                                )
                            ))
                            # キーワード追加
                            if i==0: menu = '[COLOR khaki]%s%s[/COLOR]' % (Const.STR(30057),p['title'])
                            if i>0: menu = '[COLOR lightgreen]%s%s[/COLOR]' % (Const.STR(30057),p['title'])
                            contextmenu.append((menu,
                                'RunPlugin({url}?action=addKeyword&key={key}&day={day}&ch={ch})'.format(
                                    url=sys.argv[0],
                                    key=urllib.quote_plus(p['title'].encode('utf-8')),
                                    day=str(int(strptime(p['ft'],'%Y%m%d%H%M%S').strftime('%w'))+1),
                                    ch=urllib.quote_plus(s['name'].encode('utf-8'))
                                )
                            ))
                if id.find('misc_') == 0:
                    id1 = int(id.replace('misc_',''))
                    contextmenu.append((Const.STR(30319), 'RunPlugin(%s?action=beginEditStation&id=%d)' % (sys.argv[0],id1)))
                    contextmenu.append((Const.STR(30318), 'RunPlugin(%s?action=deleteStation&id=%d)' % (sys.argv[0],id1)))
                # アドオン設定
                contextmenu.append((Const.STR(30051), 'RunPlugin(%s?action=settings)' % (sys.argv[0])))
                # コンテクストメニュー設定
                li.addContextMenuItems(contextmenu, replaceItems=True)
                # リストアイテムを追加
                xbmcplugin.addDirectoryItem(int(sys.argv[1]), s['url'], listitem=li, isFolder=False, totalItems=len(self.stations)+1)
        # リストアイテム追加完了
        xbmcplugin.endOfDirectory(int(sys.argv[1]), succeeded=True)

    def nextAired(self):
        data = ''
        nearest = None
        now = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        for p in self.programs:
            if p['ft']:
                if p['to'] < now:
                    nearest = now
                elif p['ft'] > now:
                    if nearest is None or p['ft'] < nearest:
                        nearest = p['ft']
                data = data + p['ft']
        if nearest is None:
            nearest = 99999999999999
        else:
            nearest = str(nearest)
            nearest = int(time.mktime((
                int(nearest[0:4]),
                int(nearest[4:6]),
                int(nearest[6:8]),
                int(nearest[8:10]),
                int(nearest[10:12]),
                int(nearest[12:14]),
                0, 0, 0)))
        return (nearest, md5(data).hexdigest())
