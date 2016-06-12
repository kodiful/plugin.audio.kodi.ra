# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os, sys, glob
import re
import urllib, urllib2
import copy
import codecs
import json
import datetime, time
import xml.dom.minidom
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
import exceptions

from hashlib import md5
from PIL import Image
from cStringIO import StringIO

from resources.lib.downloads import(Downloads)
from resources.lib.keywords  import(Keywords)

from resources.lib.common import(log)
from resources.lib.common import(strptime)

from resources.lib.common import(
    __prep_interval__)

from resources.lib.common import(
    __addon_id__,
    __settings__,
    __media_path__,
    __data_path__,
    __logo_url__)

from resources.lib.common import(
    __download_path__)

def check(id):
    category = id.split('_')[0]
    try:
        if __settings__.getSetting(category) == '0': return True
        if __settings__.getSetting(category) == '1': return False
        if __settings__.getSetting(id) == 'true': return True
        if __settings__.getSetting(id) == 'false': return False
    except:
        pass
    return True

class Data:

    def __init__(self, services, renew=False):
        # インスタンス変数を初期化
        self.stations = []
        self.stations_id = {}
        self.programs = []
        self.matched_programs = []
        # 放送局データのDOM生成
        self.services = services
        xmlstr = ''
        for service in self.services:
            if renew: service.getStationFile()
            xmlstr += service.getStationData()
        dom =  xml.dom.minidom.parseString(('<stations>'+xmlstr.replace('&amp;','&').replace('&','&amp;')+'</stations>').encode('utf-8'))
        # DOMからデータ抽出
        stations = dom.getElementsByTagName('station')
        for station in stations:
            id = station.getElementsByTagName('id')[0].firstChild.data.encode('utf-8')
            name = re.sub(r'(^\s+|\s+$)', '', station.getElementsByTagName('name')[0].firstChild.data)
            s = {'id':id, 'name':name}
            s['url'] = station.getElementsByTagName('url')[0].firstChild.data
            s['logo_large'] = station.getElementsByTagName('logo_large')[0].firstChild.data
            try:
                s['options'] = station.getElementsByTagName('options')[0].firstChild.data
            except:
                s['options'] = ''
            # ロゴ
            logopath = os.path.join(__media_path__, 'logo_%s.png' % id)
            if not os.path.isfile(logopath):
                try:
                    buffer = urllib2.urlopen(s['logo_large'].encode('utf-8')).read()
                except:
                    buffer = urllib2.urlopen(__logo_url__).read()
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
            s['fanart_artist'] = s['logo_path'] = logopath
            self.stations.append(s)
            self.stations_id[id] = s

    def setPrograms(self, renew=False):
        # 全番組の配列を初期化
        self.programs = []
        # 番組データのDOM生成
        xmlstr = ''
        for service in self.services:
            if renew: service.getProgramFile()
            xmlstr += service.getProgramData()
        dom =  xml.dom.minidom.parseString(('<stations>'+xmlstr.replace('&amp;','&').replace('&','&amp;')+'</stations>').encode('utf-8'))
        # DOMからデータ抽出
        stations = dom.getElementsByTagName('station')
        for station in stations:
            # この放送局の番組の配列を初期化
            id = station.getAttribute('id').encode('utf-8')
            s = self.stations_id[id]
            s['programs'] = []
            # この放送局のDOMからデータを抽出
            programs = station.getElementsByTagName('prog')
            for program in programs:
                p = {
                    'id':  id,
                    'name': s['name'],
                    'options':  s['options'],
                    'prog': '',
                    'ft': '',
                    'to': '',
                    'ftl': '',
                    'tol': '',
                    'desc': ''
                    }
                # title,ft,to,ftl,tol
                try:
                    p['prog'] = program.getElementsByTagName('title')[0].firstChild.data.strip()
                    for attr in ['ft','to','ftl','tol']:
                        p[attr] = program.getAttribute(attr)
                except exceptions.AttributeError:
                    pass
                # desc
                desc = []
                for tag in ['sub_title','pfm','desc','info','url','subtitle','content','act','music','free']:
                    try:
                        text = program.getElementsByTagName(tag)[0].firstChild.data.strip()
                        text = re.sub(r'\s',' ',text)
                        text = re.sub(r'\s{2,}',' ',text)
                        text = re.sub(r'(^\s+|\s+$)','',text)
                        #text = text.replace('&lt;','<').replace('&gt;','>').replace('&quot;','"').replace('&amp;','&')
                        #text = text.replace('&','&amp;').replace('"','&quot;').replace('>','&gt;').replace('<','&lt;')
                    except (exceptions.IndexError,exceptions.AttributeError):
                        continue
                    desc.append('&lt;div title=&quot;%s&quot;&gt;%s&lt;/div&gt;' % (tag,text))
                p['desc'] = ''.join(desc)
                # 配列に追加
                s['programs'].append(p)
                self.programs.append(p)

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
                        if p['prog'].find(s['key']) > -1:
                            pass
                        elif s['s'] == '1' and p['desc'].find(s['key']) > -1:
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
                    if s['ch'] == __settings__.getLocalizedString(30520):
                        pass
                    elif s['ch'] == p['name']:
                        pass
                    else:
                        continue
                    # 保存済み番組名と照合
                    if s['duplicate'] == '1':
                        skip = False
                        for file in glob.glob(os.path.join(__download_path__, '*.js')):
                            js_file = os.path.join(__download_path__, file)
                            mp3_file = os.path.join(__download_path__, file.replace('.js','.mp3'))
                            if os.path.isfile(mp3_file):
                                f = codecs.open(js_file,'r','utf-8')
                                program = json.loads(f.read())['program'][0]
                                f.close()
                                if p['name'] == program['bc']:
                                    if s['s'] == '0' and p['prog'] == program['title']:
                                        # 番組名が一致する
                                        skip = True
                                        break
                                    if s['s'] == '1' and p['prog'] == program['title'] and p['desc'] == program['description']:
                                        # 番組名と詳細情報が一致する
                                        skip = True
                                        break
                        if skip: continue
                    # とりあえず追加
                    start = strptime(p['ft'],'%Y%m%d%H%M%S')
                    self.matched_programs.append({'program':p, 'start':start, 'key':s['key']})
                    log('start=',start,' name=',p['name'],' prog=',p['prog'])
                    break

    def onWatched(self):
        now = datetime.datetime.now()
        for m in self.matched_programs:
            # 開始直前であれば保存処理を開始
            wait = m['start'] - now
            if wait.days == 0 and wait.seconds < __prep_interval__:
                p = m['program']
                result = Downloads().add(
                            id=p['id'],
                            name=p['name'],
                            start=p['ft'],
                            end=p['to'],
                            prog=p['prog'],
                            desc=p['desc'],
                            options=p['options'],
                            key=m['key'])
                if result['status']:
                    log('start=',strptime(p['ft'],'%Y%m%d%H%M%S'),' name=',p['name'],' prog=',p['prog'])

    def showPrograms(self):
        # 放送局表示
        for s in self.stations:
            id = s['id']
            if check(id):
                programs = s['programs']
                title = '[COLOR white]%s[/COLOR]' % (s['name'])
                bullet = '\u25b6'
                if len(programs) == 0:
                    title += ' [COLOR khaki]%s %s[/COLOR]' % (bullet,'放送休止')
                    title0 = '放送休止'
                    comment0 = ''
                else:
                    for i in range(len(programs)):
                        p = programs[i]
                        if p['ftl'] == '':
                            prog = '%s' % (p['prog'])
                        else:
                            prog = '%s (%s:%s～%s:%s)' % (p['prog'],p['ftl'][0:2],p['ftl'][2:4],p['tol'][0:2],p['tol'][2:4])
                        if i==0: title += ' [COLOR khaki]%s %s[/COLOR]' % (bullet,prog)
                        if i>0: title += ' [COLOR lightgreen]%s %s[/COLOR]' % (bullet,prog)
                    title0 = programs[0]['prog']
                    comment0 = re.sub(r'&lt;.*?&gt;','',programs[0]['desc'])
                # リストアイテムを定義
                li = xbmcgui.ListItem(title, iconImage=s['fanart_artist'], thumbnailImage=s['fanart_artist'])
                li.setInfo(type='music', infoLabels={'title':title0,'artist':s['name'],'comment':comment0})
                # コンテクストメニュー
                contextmenu = []
                # 保存済み番組
                if __settings__.getSetting('download') == 'true':
                    contextmenu.append((__settings__.getLocalizedString(30312), 'XBMC.Container.Update(%s?action=showKeywords)' % (sys.argv[0])))
                # 番組情報を更新
                contextmenu.append((__settings__.getLocalizedString(30055), 'XBMC.Container.Update(%s,replace)' % (sys.argv[0])))
                # 保存、設定
                if __settings__.getSetting('download') == 'true':
                    if s['options']:
                        for i in range(len(programs)):
                            p = programs[i]
                            if p['ft'].isdigit() and p['to'].isdigit():
                                # 保存
                                if i==0: menu = '[COLOR khaki]%s%s[/COLOR]' % (__settings__.getLocalizedString(30056),p['prog'])
                                if i>0: menu = '[COLOR lightgreen]%s%s[/COLOR]' % (__settings__.getLocalizedString(30056),p['prog'])
                                contextmenu.append((menu,
                                    'XBMC.RunPlugin({url}?action=addDownload&id={id}&name={name}&start={start}&end={end}&prog={prog}&desc={desc}&options={options})'.format(
                                        url=sys.argv[0],
                                        id=id,
                                        name=urllib.quote_plus(s['name'].encode('utf-8')),
                                        start=p['ft'],
                                        end=p['to'],
                                        prog=urllib.quote_plus(p['prog'].encode('utf-8')),
                                        desc=urllib.quote_plus(p['desc'].encode('utf-8')),
                                        options=urllib.quote_plus(s['options'])
                                    )
                                ))
                                # キーワード追加
                                if i==0: menu = '[COLOR khaki]%s%s[/COLOR]' % (__settings__.getLocalizedString(30057),p['prog'])
                                if i>0: menu = '[COLOR lightgreen]%s%s[/COLOR]' % (__settings__.getLocalizedString(30057),p['prog'])
                                contextmenu.append((menu,
                                    'XBMC.RunPlugin({url}?action=addKeyword&key={key}&day={day}&ch={ch})'.format(
                                        url=sys.argv[0],
                                        key=urllib.quote_plus(p['prog'].encode('utf-8')),
                                        day=str(int(strptime(p['ft'],'%Y%m%d%H%M%S').strftime('%w'))+1),
                                        ch=urllib.quote_plus(s['name'].encode('utf-8'))
                                    )
                                ))
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