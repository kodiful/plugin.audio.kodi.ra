# -*- coding: utf-8 -*-

from resources.lib.const import Const, Resumes, Birth
from resources.lib.common import *

import sys, os, platform
import re, glob
import time
import urlparse
import codecs
import subprocess
import json, xml.dom.minidom
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

from hashlib import md5

from resources.lib.cp.radiko import Radiko, getAuthkey, authenticate
from resources.lib.cp.radiru import Radiru
from resources.lib.cp.jcba   import Jcba
from resources.lib.cp.misc   import Misc
from resources.lib.data      import Data
from resources.lib.downloads import Downloads
from resources.lib.keywords  import Keywords

# HTTP接続におけるタイムアウト(秒)
import socket
socket.setdefaulttimeout(60)

class Params:
    BIRTH_FILE   = os.path.join(Const.DATA_PATH, '_birth')
    ALIVE_FILE   = os.path.join(Const.DATA_PATH, '_alive')
    RESUME_FILE  = os.path.join(Const.DATA_PATH, '_resume')


#-------------------------------------------------------------------------------
class Monitor(xbmc.Monitor):

    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)

    def onSettingsChanged(self):
        log('settings changed')

    def onScreensaverActivated(self):
        log('screensaver activated')

    def onScreensaverDeactivated(self):
        log('screensaver deactivated')

#-------------------------------------------------------------------------------
def checkSettings(filepath=Const.USERSETTINGS_FILE):
    settings = read_file(filepath)
    return md5(settings).hexdigest() if settings else ''

#-------------------------------------------------------------------------------
def checkKeywords(filepath=Const.KEYWORDS_FILE):
    if os.path.isfile(filepath):
        return os.path.getmtime(filepath)
    else:
        return 0

#-------------------------------------------------------------------------------
def checkDownloads(filepath=Const.EXIT_FILE):
    if os.path.isfile(filepath):
        os.remove(filepath)
        return 1
    else:
        return 0

#-------------------------------------------------------------------------------
def setResumes(filepath=Params.RESUME_FILE):
    global Resumes
    write_json(filepath, Resumes)

#-------------------------------------------------------------------------------
def getResumes(filepath=Params.RESUME_FILE):
    global Resumes
    Resumes = read_json(filepath)

#-------------------------------------------------------------------------------
def setAlive(filepath=Params.ALIVE_FILE):
    write_file(filepath, '')
    return os.path.getmtime(filepath)

#-------------------------------------------------------------------------------
def getAlive(filepath=Params.ALIVE_FILE):
    if os.path.isfile(filepath) and time.time() < os.path.getmtime(filepath) + Const.DEAD_INTERVAL:
        return True
    else:
        return False

#-------------------------------------------------------------------------------
def setBirth(filepath=Params.BIRTH_FILE):
    write_file(filepath, '')
    return os.path.getmtime(filepath)

#-------------------------------------------------------------------------------
def getBirth(filepath=Params.BIRTH_FILE):
    global Birth
    if os.path.isfile(filepath) and Birth == os.path.getmtime(filepath):
        return True
    else:
        return False

#-------------------------------------------------------------------------------
def clearResumes():
    # ファイルをクリア
    for f in glob.glob(os.path.join(Const.DATA_PATH, '_*')):
        try:
            if os.path.isfile(f): os.remove(f)
            if os.path.isdir(f): os.rmdir(f)
        except:
            pass

#-------------------------------------------------------------------------------
def resetAll():
    # インストール後に生成されたファイルをすべて削除（保存フォルダを除く）
    try:
        # プロファイルの配下を削除
        for root, dirs, files in os.walk(Const.PROFILE_PATH, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
        # プロファイルディレクトリを削除
        os.rmdir(Const.PROFILE_PATH)
        # 設定ダイアログを削除
        os.remove(Const.SETTINGS_FILE)
    except:
        pass
    # 初期化
    initialize()

#-------------------------------------------------------------------------------
def reset():
    # 設定ダイアログを削除
    if os.path.isfile(Const.SETTINGS_FILE):
        os.remove(Const.SETTINGS_FILE)
    # 初期化
    initialize()

#-------------------------------------------------------------------------------
def setup(radiru, radiko, jcba, misc):
    # テンプレート読み込み
    template = read_file(Const.TEMPLATE_FILE)
    # 放送局リスト
    s = [Const.STR(30520)]
    stations = Data((radiru,radiko)).stations
    for station in stations:
        s.append(station['name'])
    # ソース作成
    ffmpeg = os.path.join('usr','local','bin','ffmpeg')
    if not os.path.isfile(ffmpeg): ffmpeg = ''
    source = template.format(
        radiru = radiru.getSettingsData(),
        radiko = radiko.getSettingsData(),
        jcba   = jcba.getSettingsData(),
        misc   = misc.getSettingsData(),
        bc = '|'.join(s),
        ffmpeg = ffmpeg,
        os = platform.system())
    # ファイル書き込み
    write_file(Const.SETTINGS_FILE, source)
    # ログ
    log('settings updated')

#-------------------------------------------------------------------------------
def main():
    global Resumes
    global Birth

    # ログ
    log('path=',xbmc.getInfoLabel('Container.FolderPath'))
    log('argv=', sys.argv)


    args = urlparse.parse_qs(sys.argv[2][1:], keep_blank_values=True)
    for key in args.keys():
        args[key] = args[key][0]
    params = {'action':''}
    params.update(args)

    '''# パラメータ抽出
    parsed = urlparse.parse_qs(urlparse.urlparse(sys.argv[2]).query, keep_blank_values=True)
    params = {'action':''}
    for key in parsed.keys():
        value = params[key.decode('utf-8')] = parsed[key][0].decode('utf-8')'''

    log(params)

    # アドオン設定をコピー
    settings = {}
    for key in ['id','key','s','day','ch','duplicate','name','stream']:
        settings[key] = Const.GET(key)
    # アドオン設定をリセット
    Const.SET('id','')
    Const.SET('key','')
    Const.SET('s','0')
    Const.SET('day','0')
    Const.SET('ch','0')
    Const.SET('duplicate','0')
    Const.SET('name','')
    Const.SET('stream','')

    # actionに応じた処理

    # リセット
    if params['action'] == 'resetAll':
        resetAll()
    elif params['action'] == 'reset':
        reset()

    # ダウンロードの管理
    elif params['action'] == 'addDownload':
        status = Downloads().add(
            id=params['id'],
            name=params['name'],
            start=params['start'],
            end=params['end'],
            title=params['title'],
            description=params['description'],
            source=params['source'],
            lag=params['lag'])
        if status:
            notify(status, error=True)
        else:
            notify('Download started/reserved successfully', time=3000)
    elif params['action'] == 'showDownloads':
        Downloads().show()
    elif params['action'] == 'clearDownloads':
        Downloads().deleteall()
    elif params['action'] == 'deleteDownload':
        Downloads().delete(params['id'])
    elif params['action'] == 'showContents':
        Downloads().show(params['key'])
    elif params['action'] == 'updateRSS':
        Downloads().createRSS()

    # キーワードの追加、変更、削除
    elif params['action'] == 'addKeyword':
        Keywords().add(
            key=params['key'],
            day=params['day'],
            ch=params['ch'])
    elif params['action'] == 'showKeywords':
        Keywords().show()
    elif params['action'] == 'beginEditKeyword':
        Keywords().beginEdit(params['id'])
    elif params['action'] == 'endEditKeyword':
        settings = {}
        for key in ['id','key','s','day','ch','duplicate']:
            settings[key] = Const.GET(key)
        Keywords().endEdit(
            id=settings['id'],
            key=settings['key'],
            s=settings['s'],
            day=settings['day'],
            ch=settings['ch'],
            duplicate=settings['duplicate'])
    elif params['action'] == 'deleteKeyword':
        Keywords().delete(params['id'])

    # 放送局の追加、変更、削除
    elif params['action'] == 'beginEditStation':
        Misc().beginEdit(params['id'])
    elif params['action'] == 'endEditStation':
        Misc().endEdit(
            settings['id'],
            settings['name'],
            settings['stream'])
        xbmc.executebuiltin('Container.Refresh()')
    elif params['action'] == 'deleteStation':
        Misc().delete(params['id'])
        xbmc.executebuiltin('Container.Refresh()')

    # アドオン設定
    elif params['action'] == 'settings':
        Const.SET('id','')
        Const.SET('key','')
        Const.SET('s','0')
        Const.SET('day','0')
        Const.SET('ch','0')
        Const.SET('duplicate','0')
        Const.SET('name','')
        Const.SET('stream','')
        xbmc.executebuiltin('Addon.OpenSettings(%s)' % Const.ADDON_ID)

    # 表示
    elif params['action'] == 'showPrograms':
        start()
    else:
        if Const.GET('download') == 'true':
            Keywords().show()
        else:
            start()

#-------------------------------------------------------------------------------
def start(background=False):
    global Resumes
    global Birth
    # ディレクトリをチェック
    if not os.path.isdir(Const.CACHE_PATH): os.makedirs(Const.CACHE_PATH)
    if not os.path.isdir(Const.MEDIA_PATH): os.makedirs(Const.MEDIA_PATH)
    if not os.path.isdir(Const.DATA_PATH):  os.makedirs(Const.DATA_PATH)
    # 初期化
    if os.path.isfile(Const.SETTINGS_FILE) and getAlive():
        data = proceed()
    else:
        data = initialize()
    # 表示
    if not background: data.showPrograms()
    # Birth設定
    Birth = setBirth()
    # Alive設定を更新
    setAlive()
    # 更新
    monitor = Monitor()
    while not monitor.abortRequested():
        if monitor.waitForAbort(Const.CHECK_INTERVAL):
            log('break by aborted')
            clearResumes();
            break
        if not getBirth():
            log('break by renewed')
            break
        # Const.CHECK_INTERVAL毎に実行
        data = watcher(data)
        # Alive設定を更新
        setAlive()

#-------------------------------------------------------------------------------
def initialize():
    global Resumes
    # _birth,_resumeを削除
    clearResumes()
    # radiko認証
    getAuthkey()
    auth = authenticate()
    auth.start()
    while 'authed' not in auth._response or auth._response['authed'] == 0: time.sleep(1)
    if auth._response['area_id'] == '': notify('Radiko authentication failed', error=True)
    # クラス初期化
    radiru = Radiru(renew=True)
    radiko = Radiko(area=auth._response['area_id'], token=auth._response['auth_token'], renew=True)
    jcba   = Jcba(renew=True)
    misc   = Misc(renew=True)
    data   = Data((radiru,radiko,jcba,misc))
    # 放送局データに応じて設定画面を生成
    setup(radiru, radiko, jcba, misc)
    # 番組データを取得
    data.setPrograms(renew=True)
    # 更新を通知
    data.onChanged()
    # Resumes設定
    (reinfo, hashinfo) = data.nextAired()
    Resumes['key'] = auth._response['partial_key']
    Resumes['token'] = auth._response['auth_token']
    Resumes['area'] = auth._response['area_id']
    Resumes['reinfo'] = reinfo
    Resumes['hashinfo'] = hashinfo
    Resumes['reauth'] = int(time.time()) + Const.RESUME_TIMER_INTERVAL
    Resumes['settings'] = checkSettings()
    Resumes['keywords'] = checkKeywords()
    setResumes()
    # Dataオブジェクトを返す
    return data

#-------------------------------------------------------------------------------
def proceed():
    global Resumes
    # Resumes設定
    getResumes()
    # クラス初期化
    radiru = Radiru()
    radiko = Radiko(area=Resumes['area'], token=Resumes['token'])
    jcba   = Jcba()
    misc   = Misc()
    data   = Data((radiru,radiko,jcba,misc))
    # 番組データ
    data.setPrograms()
    # 更新を通知
    data.onChanged()
    # Dataオブジェクトを返す
    return data

#-------------------------------------------------------------------------------
def watcher(data):
    global Resumes
    # 現在時刻
    stamp = setAlive()
    log('path=',xbmc.getInfoLabel('Container.FolderPath'),
        ' dialog=',xbmcgui.getCurrentWindowDialogId())
    log('reinfo=',int(Resumes['reinfo']-stamp),
        ' reauth=',int(Resumes['reauth']-stamp),
        ' update=',Resumes['update'])

    # 予約された画面更新がある場合
    if Resumes['update'] and refresh():
        pass

    # 番組情報が更新された場合
    elif Resumes['reinfo'] < stamp:
        # 番組データ
        data.setPrograms(renew=True)
        # 更新をチェック
        (reinfo, hashinfo) = data.nextAired()
        if Resumes['hashinfo'] != hashinfo:
            Resumes['reinfo'] = reinfo
            Resumes['hashinfo'] = hashinfo
            # 更新を通知
            data.onChanged()
            # 画面更新
            refresh()
        else:
            log('hashinfo unchanged')

    # 設定変更があった場合
    elif Resumes['settings'] != checkSettings() or Resumes['keywords'] != checkKeywords():
        Resumes['settings'] = checkSettings()
        Resumes['keywords'] = checkKeywords()
        # 更新を通知
        data.onChanged()
        # 画面更新
        refresh()

    # radiko認証の期限が切れた場合
    elif Resumes['reauth'] < stamp:
        # radiko認証
        auth = authenticate()
        auth.start()
        while 'authed' not in auth._response or auth._response['authed'] == 0: time.sleep(0.1)
        if auth._response['area_id'] == '': notify('Radiko authentication failed', error=True)
        # Resumes設定
        Resumes['key'] = auth._response['partial_key']
        Resumes['token'] = auth._response['auth_token']
        Resumes['area'] = auth._response['area_id']
        Resumes['reauth'] = stamp + Const.RESUME_TIMER_INTERVAL
        # radiko認証の更新に伴う処理
        radiru = Radiru()
        radiko = Radiko(area=Resumes['area'], token=Resumes['token'], renew=True)
        jcba   = Jcba()
        misc   = Misc()
        data   = Data((radiru,radiko,jcba,misc))
        # 番組データを更新
        data.setPrograms(renew=True)
        # 更新を通知
        data.onChanged()
        # 画面更新
        refresh()

    # キーワードマッチによるダウンロード
    if Const.GET('download') == 'true':
        data.onWatched()

    # ダウンロードが完了している場合
    if checkDownloads():
        notify('Download completed')
        if Const.GET('rss') == 'true': Downloads().createRSS()

    # Resumes設定を書き込み
    setResumes()

    log('stations=',len(data.stations),' programs=',len(data.programs),' matched_programs=',len(data.matched_programs))
    return data

def refresh():
    global Resumes
    # カレントウィンドウをチェック
    immediate = False
    if xbmcgui.getCurrentWindowDialogId() == 9999:
        path = xbmc.getInfoLabel('Container.FolderPath')
        if path == sys.argv[0] and Const.GET('download') == 'false':
            immediate = True
        elif path == '%s?action=showPrograms' % sys.argv[0]:
            immediate = True

    # 画面を更新
    if immediate:
        xbmc.executebuiltin('Container.Update(%s?action=showPrograms,replace)' % (sys.argv[0]))
        Resumes['update'] = False
        log('update immediately')
    else:
        Resumes['update'] = True
        log('update scheduled')
    return immediate

#-------------------------------------------------------------------------------
if __name__  == '__main__': main()
