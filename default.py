# -*- coding: utf-8 -*-

import sys, os, string
import re, glob, shutil
import xml.dom.minidom
import threading, time
import urllib2
import codecs
import json
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

from hashlib import md5
from PIL import Image
from cStringIO import StringIO

from resources.lib.radiko import(Radiko,getAuthkey,authenticate)
from resources.lib.radiru import(Radiru)
from resources.lib.simul  import(Simul)

from resources.lib.common import(
    __addon_id__,
    __settings__,
    __profile_path__,
    __cache_path__,
    __media_path__,
    __data_path__)

from resources.lib.common import(
    __settings_file__,
    __template_file__,
    __usersettings_file__)

from resources.lib.common import(
    __resume_timer_interval__,
    __check_interval__,
    __dead_interval__)

from resources.lib.common import(notify)

__logo_url__    = 'http://kodiful.com/KodiRa/downloads/simul/icon.png'

__birth_file__  = os.path.join(__data_path__, '_birth')
__alive_file__  = os.path.join(__data_path__, '_alive')
__resume_file__ = os.path.join(__data_path__, '_resume')

Resumes = {
    "key":      None,
    "token":    None,
    "area":     None,
    "reinfo":   None,
    "hashinfo": None,
    "reauth":   None,
    "settings": None}

#-------------------------------------------------------------------------------
def deadOrAlive(aliveFile=__alive_file__):
    stamp = int(time.time())
    if not os.path.isfile(aliveFile): return 1
    while True:
        try:
            check = os.path.getmtime(aliveFile)
            if stamp - check > __dead_interval__: return 1
            else : return 0
            break
        except:
            pass
        time.sleep(.05)

#-------------------------------------------------------------------------------
def checkSettings(settingsFile=__usersettings_file__):
    if not os.path.isfile(settingsFile): return 0
    return os.path.getmtime(settingsFile)

#-------------------------------------------------------------------------------
def setResumes(resumeFile=__resume_file__):
    global Resumes
    f = codecs.open(resumeFile,'w','utf-8')
    f.write(json.dumps(Resumes))
    f.close()

#-------------------------------------------------------------------------------
def getResumes(resumeFile=__resume_file__):
    global Resumes
    f = codecs.open(resumeFile,'r','utf-8')
    Resumes = json.loads(f.read())
    f.close()

#-------------------------------------------------------------------------------
def birth(birthFile=__birth_file__):
    f = codecs.open(birthFile,'w','utf-8')
    f.write('')
    f.close()
    return os.path.getmtime(birthFile)

#-------------------------------------------------------------------------------
def birthCheck(birthFile=__birth_file__):
    global BirthTime
    if BirthTime != os.path.getmtime(birthFile):
        return True
    return False

#-------------------------------------------------------------------------------
def keepAlive(aliveFile=__alive_file__):
    f = codecs.open(aliveFile,'w','utf-8')
    f.write('')
    f.close()

#-------------------------------------------------------------------------------
def clearCache():
    files = glob.glob(os.path.join(__data_path__, '_*'))
    for f in files:
        try:
            if os.path.isfile(f): os.remove(f)
            if os.path.isdir(f): os.rmdir(f)
        except:
            pass

#-------------------------------------------------------------------------------
def getStationFile(services):
    for service in services:
        service.getStationFile()

#-------------------------------------------------------------------------------
def getProgramFile(services):
    for service in services:
        service.getProgramFile()

#-------------------------------------------------------------------------------
def getStationDOM(services):
    xmlstr = ''
    for service in services:
        xmlstr += service.getStationArray()
    return xml.dom.minidom.parseString(('<stations>'+xmlstr.replace('&amp;','&').replace('&','&amp;')+'</stations>').encode('utf-8'))

#-------------------------------------------------------------------------------
def getProgramDOM(services):
    xmlstr = ''
    for service in services:
        xmlstr += service.getProgramArray()
    return xml.dom.minidom.parseString(('<stations>'+xmlstr.replace('&amp;','&').replace('&','&amp;')+'</stations>').encode('utf-8'))

#-------------------------------------------------------------------------------
def checkStationID(id):
    category = id.split('_')[0]
    try:
        if __settings__.getSetting(category) == '0': return True
        if __settings__.getSetting(category) == '1': return False
        if __settings__.getSetting(id) == 'true': return True
        if __settings__.getSetting(id) == 'false': return False
    except:
        pass
    return True

#-------------------------------------------------------------------------------
def buildSettings(services):
    # 設定画面がない場合は生成する
    if os.path.isfile(__settings_file__) and os.path.isdir(__profile_path__):
        pass
    else:
        # テンプレート読み込み
        f = codecs.open(__template_file__,'r','utf-8')
        template = f.read()
        f.close()
        source = template.format(
            radiru = services[0].getSettingsArray(),
            radiko = services[1].getSettingsArray(),
            simul  = services[2].getSettingsArray(),
            reset  = 'RunPlugin(plugin://%s/?action=reset)' % __addon_id__)
        # ファイル書き込み
        f = codecs.open(__settings_file__,'w','utf-8')
        f.write(source)
        f.close()

#-------------------------------------------------------------------------------
def buildStationList(stationDOM, programDOM):

    # 放送局データ
    items = {}
    stations = stationDOM.getElementsByTagName('station')
    number_of_stations = stations.length
    for station in stations:
        id = station.getElementsByTagName('id')[0].firstChild.data.encode('utf-8')
        if checkStationID(id):
            items[id] = {}
            items[id]['name'] = re.sub(r'(^\s+|\s+$)', '', station.getElementsByTagName('name')[0].firstChild.data)
            items[id]['url'] = station.getElementsByTagName('url')[0].firstChild.data
            items[id]['logo_large'] = station.getElementsByTagName('logo_large')[0].firstChild.data
            # ロゴ
            logopath = os.path.join(__media_path__, 'logo_%s.png' % id)
            if not os.path.isfile(logopath):
                try:
                    buffer = urllib2.urlopen(items[id]['logo_large'].encode('utf-8')).read()
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
            items[id]['fanart_artist'] = items[id]['logo_path'] = logopath

    # 番組データ
    stations = programDOM.getElementsByTagName('station')
    for station in stations:
        id = station.getAttribute('id').encode('utf-8')
        if checkStationID(id):
            programs = station.getElementsByTagName('prog')
            for i in range(programs.length):
                items[id][i] = {}
                try:
                    items[id][i]['prog'] = programs[i].getElementsByTagName('title')[0].firstChild.data.strip()
                except:
                    items[id][i]['prog'] = ''
                try:
                    items[id][i]['start'] = programs[i].getAttribute('ftl')
                except:
                    items[id][i]['start'] = ''
                try:
                    items[id][i]['end'] = programs[i].getAttribute('tol')
                except:
                    items[id][i]['end'] = ''
                try:
                    items[id][i]['desc'] = programs[i].getElementsByTagName('desc')[0].firstChild.data.strip()
                except:
                    try:
                        items[id][i]['desc'] = programs[i].getElementsByTagName('info')[0].firstChild.data.strip()
                    except:
                        items[id][i]['desc'] = ''
                items[id][i]['desc'] = re.sub(r'&lt;.*?&gt;', '', items[id][i]['desc'])

    # 表示
    stations = programDOM.getElementsByTagName('station')
    for station in stations:
        id = station.getAttribute('id').encode('utf-8')
        if checkStationID(id):
            programs = station.getElementsByTagName('prog')
            title = '[COLOR green]%s[/COLOR]' % (items[id]['name'])
            bullet = u'\u25b6'.encode('utf-8')
            if programs.length == 0:
                title += (' [COLOR green]'+bullet+'[/COLOR] %s').decode('utf-8') % ('放送休止'.decode('utf-8'))
            else:
                for i in range(programs.length):
                    if items[id][i]['start'] == '':
                        prog = '%s'.decode('utf-8') % (items[id][i]['prog'])
                    else:
                        prog = '%s (%s:%s～%s:%s)'.decode('utf-8') % (items[id][i]['prog'],items[id][i]['start'][0:2],items[id][i]['start'][2:4],items[id][i]['end'][0:2],items[id][i]['end'][2:4])
                    title += (' [COLOR green]'+bullet+'[/COLOR] %s').decode('utf-8') % (prog)
            # リストアイテムを定義
            li = xbmcgui.ListItem(title, iconImage=items[id]['fanart_artist'], thumbnailImage=items[id]['fanart_artist'])
            #li.setInfo(type='music', infoLabels={'title':title, 'artist':items[id]['now_desc']})
            li.setInfo(type='music', infoLabels={'title':title})
            # コンテクストメニュー
            contextmenu = []
            contextmenu.append((__settings__.getLocalizedString(30055), 'XBMC.Container.Refresh'))
            contextmenu.append((__settings__.getLocalizedString(30051), 'Addon.OpenSettings(%s)' % __addon_id__))
            li.addContextMenuItems(contextmenu, replaceItems=True)
            # リストアイテムを追加
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), items[id]['url'], listitem=li, isFolder=False, totalItems=number_of_stations)
    # リストアイテム追加完了
    xbmcplugin.endOfDirectory(int(sys.argv[1]), succeeded=True)

#-------------------------------------------------------------------------------
def getNearestTime(programDOM):
    data = ''
    nearest = 0
    stations = programDOM.getElementsByTagName('station')
    for i in range(stations.length):
        id = stations[i].getAttribute('id').encode('utf-8')
        if checkStationID(id):
            try:
                ft0 = stations[i].getElementsByTagName('prog')[0].getAttribute('ft')
            except:
                continue
            try:
                ft1 = stations[i].getElementsByTagName('prog')[1].getAttribute('ft')
            except:
                continue
            data = data+ft0+ft1
            ft1 = int(ft1)
            if nearest == 0 or nearest > ft1:
                nearest = ft1
    if nearest == 0:
        nearest = '99999999999999'
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

#-------------------------------------------------------------------------------
def main():
    # パラメータ抽出
    params = {'action':''}
    if len(sys.argv[2]) > 0:
        pairs = re.compile(r'[?&]').split(sys.argv[2])
        for i in range(len(pairs)):
            splitparams = pairs[i].split('=')
            if len(splitparams) == 2:
                params[splitparams[0]] = splitparams[1]
    # actionに応じた処理
    if params['action'] == 'reset':
        reset()
    else:
        default()


def reset():
    # インストール後に生成されたファイルをすべて削除
    try:
        for root, dirs, files in os.walk(__profile_path__, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(__profile_path__)
        os.remove(__settings_file__)
    except:
        pass
    # リフレッシュ
    notify('Initializing KodiRa', image='DefaultIconInfo.png')
    xbmc.executebuiltin("XBMC.Container.Refresh")


def default():
    # グローバル変数
    global Resumes
    global BirthTime
    # モード判定
    if deadOrAlive():
        # 初期モード
        clearCache()
        # radiko認証
        getAuthkey()
        auth = authenticate()
        auth.start()
        while 'authed' not in auth._response or auth._response['authed'] == 0: time.sleep(1)
        if auth._response['area_id'] == '': notify('Radiko authentication failed')
        # クラス初期化
        radiko = Radiko(auth._response['area_id'], auth._response['auth_token'])
        radiru = Radiru()
        simul  = Simul()
        services = (radiru,radiko,simul)
        # 放送局データ取得
        getStationFile(services)
        # 放送局データ統合
        stationDOM = getStationDOM(services)
        # 放送局データに応じて設定画面を生成
        buildSettings(services)
        # 番組データ取得
        getProgramFile(services)
        # 番組データ統合
        programDOM = getProgramDOM(services)
        # Resumes設定
        (reinfo, hashinfo) = getNearestTime(programDOM)
        Resumes['key'] = auth._response['partial_key']
        Resumes['token'] = auth._response['auth_token']
        Resumes['area'] = auth._response['area_id']
        Resumes['reinfo'] = reinfo
        Resumes['hashinfo'] = hashinfo
        Resumes['reauth'] = int(time.time()) + __resume_timer_interval__
        Resumes['settings'] = checkSettings()
        setResumes()
    else:
        # 継続モード
        getResumes()
        # クラス初期化
        radiko = Radiko(Resumes['area'], Resumes['token'])
        radiru = Radiru()
        simul  = Simul()
        services = (radiru,radiko,simul)
        # 放送局データ統合
        stationDOM = getStationDOM(services)
        # 番組データ統合
        programDOM = getProgramDOM(services)

    # 表示
    buildStationList(stationDOM, programDOM)
    # BirthTime設定
    BirthTime = birth()
    # スレッド開始
    threading.Thread(target=updateInfo).start()

#-------------------------------------------------------------------------------
def updateInfo():

    global Resumes

    if birthCheck():
        print 'updateInfo:birthCheck'
        return # プロセスが別に起動した場合
    elif xbmcgui.getCurrentWindowId() != 10501 and xbmcgui.getCurrentWindowId() >= 13000:
        print 'updateInfo:WindowId'
        return # WindowIDが変わった場合
    else:
        stamp = int(time.time())
        if Resumes['reauth'] < stamp:
            # radiko認証
            auth = authenticate()
            auth.start()
            while 'authed' not in auth._response or auth._response['authed'] == 0: time.sleep(0.1)
            if auth._response['area_id'] == '': notify('Radiko authentication failed')
            # Resumes設定
            Resumes['key'] = auth._response['partial_key']
            Resumes['token'] = auth._response['auth_token']
            Resumes['area'] = auth._response['area_id']
            Resumes['reauth'] = stamp + __resume_timer_interval__
            setResumes()
            keepAlive()
            xbmc.executebuiltin("XBMC.Container.Refresh")
            print 'updateInfo:reauth'
            return # 番組データ更新
        if Resumes['reinfo'] < stamp:
            # クラス初期化
            radiko = Radiko(Resumes['area'], Resumes['token'])
            radiru = Radiru()
            simul  = Simul()
            services = (radiko, radiru, simul)
            # 放送局データ取得
            getStationFile(services)
            # 放送局データ統合
            stationDOM = getStationDOM(services)
            # 番組データ取得
            getProgramFile(services)
            # 番組データ統合
            programDOM = getProgramDOM(services)
            # 更新をチェック
            (reinfo, hashinfo) = getNearestTime(programDOM)
            if Resumes['hashinfo'] != hashinfo:
                Resumes['reinfo'] = reinfo
                Resumes['hashinfo'] = hashinfo
                setResumes()
                keepAlive()
                xbmc.executebuiltin("XBMC.Container.Refresh")
                print 'updateInfo:Refresh'
                return # 番組データ更新
            # 更新予定だが未更新の場合
            threading.Timer(__check_interval__, updateInfo).start()
            print 'updateInfo:Timer'
            return
        if Resumes['settings'] < checkSettings():
            Resumes['settings'] = checkSettings()
            setResumes()
            keepAlive()
            xbmc.executebuiltin("XBMC.Container.Refresh")
            print 'updateInfo:settings'
            return # 表示更新

    keepAlive()
    threading.Timer(__check_interval__, updateInfo).start()

#-------------------------------------------------------------------------------
if __name__  == '__main__': main()
