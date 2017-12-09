# -*- coding: utf-8 -*-

import sys, os, platform
import re, glob
import time
import urlparse
import codecs
import subprocess
import json, xml.dom.minidom
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

from hashlib import md5

from resources.lib.radiru    import(Radiru)
from resources.lib.radiko    import(Radiko,getAuthkey,authenticate)
from resources.lib.jcba      import(Jcba)
from resources.lib.misc      import(Misc)
from resources.lib.data      import(Data)
from resources.lib.downloads import(Downloads)
from resources.lib.keywords  import(Keywords)

from resources.lib.common import(
    __addon__,
    __profile_path__,
    __cache_path__,
    __media_path__,
    __data_path__,
    __template_path__)

from resources.lib.common import(
    __settings_file__,
    __template_file__,
    __keywords_file__,
    __usersettings_file__,
    __rss_file__,
    __exit_file__)

from resources.lib.common import(
    __resume_timer_interval__,
    __check_interval__,
    __dead_interval__)

from resources.lib.common import(log)
from resources.lib.common import(notify,notify2)
from resources.lib.common import(Resumes,Birth)

__birth_file__   = os.path.join(__data_path__, '_birth')
__alive_file__   = os.path.join(__data_path__, '_alive')
__resume_file__  = os.path.join(__data_path__, '_resume')


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
def checkSettings(settingsFile=__usersettings_file__):
    if not os.path.isfile(settingsFile): return ''
    f = codecs.open(settingsFile,'r','utf-8')
    settings = f.read()
    f.close()
    return md5(settings.encode('utf-8','ignore')).hexdigest()

#-------------------------------------------------------------------------------
def checkKeywords(keywordsFile=__keywords_file__):
    if not os.path.isfile(keywordsFile): return 0
    return os.path.getmtime(keywordsFile)

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
def setAlive(aliveFile=__alive_file__):
    f = codecs.open(aliveFile,'w','utf-8')
    f.write('')
    f.close()
    return os.path.getmtime(aliveFile)

#-------------------------------------------------------------------------------
def getAlive(aliveFile=__alive_file__):
    if os.path.isfile(aliveFile) and time.time() < os.path.getmtime(aliveFile) + __dead_interval__:
        return True
    else:
        return False

#-------------------------------------------------------------------------------
def setBirth(birthFile=__birth_file__):
    f = codecs.open(birthFile,'w','utf-8')
    f.write('')
    f.close()
    return os.path.getmtime(birthFile)

#-------------------------------------------------------------------------------
def getBirth(birthFile=__birth_file__):
    global Birth
    if os.path.isfile(birthFile) and Birth == os.path.getmtime(birthFile):
        return True
    else:
        return False

#-------------------------------------------------------------------------------
def clearResumes():
    # ファイルをクリア
    files = glob.glob(os.path.join(__data_path__, '_*'))
    for f in files:
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
        for root, dirs, files in os.walk(__profile_path__, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
        # プロファイルディレクトリを削除
        os.rmdir(__profile_path__)
        # 設定ダイアログを削除
        os.remove(__settings_file__)
    except:
        pass
    # 初期化
    initialize()

#-------------------------------------------------------------------------------
def reset():
    # 設定ダイアログを削除
    if os.path.isfile(__settings_file__):
        os.remove(__settings_file__)
    # 初期化
    initialize()

#-------------------------------------------------------------------------------
def setup(radiru, radiko, jcba, misc):
    # テンプレート読み込み
    f = codecs.open(__template_file__,'r','utf-8')
    template = f.read()
    f.close()
    # 放送局リスト
    s = [__addon__.getLocalizedString(30520)]
    stations = Data((radiru,radiko,jcba,misc)).stations
    for station in stations:
        s.append(station['name'])
    # ソース作成
    ffmpeg = '/usr/local/bin/ffmpeg'
    if not os.path.isfile(ffmpeg): ffmpeg = ''
    rtmpdump = '/usr/local/bin/rtmpdump'
    if not os.path.isfile(rtmpdump): rtmpdump = ''
    source = template.format(
        radiru = radiru.getSettingsData(),
        radiko = radiko.getSettingsData(),
        jcba   = jcba.getSettingsData(),
        misc   = misc.getSettingsData(),
        bc = '|'.join(s),
        ffmegpath = ffmpeg,
        rtmpdumppath = rtmpdump,
        os = platform.system())
    # ファイル書き込み
    f = codecs.open(__settings_file__,'w','utf-8')
    f.write(source)
    f.close()
    # ログ
    log('settings updated')

#-------------------------------------------------------------------------------
def main():
    global Resumes
    global Birth
    # ログ
    log('path=',xbmc.getInfoLabel('Container.FolderPath'))
    # パラメータ抽出
    parsed = urlparse.parse_qs(urlparse.urlparse(sys.argv[2]).query, keep_blank_values=True)
    params = {'action':''}
    for key in parsed.keys():
        value = params[key.decode('utf-8')] = parsed[key][0].decode('utf-8')
        log('argv:',key,'=',value)
    # アドオン設定をコピー
    settings = {}
    for key in ['id','key','s','day','ch','duplicate','name','stream']:
        settings[key] = __addon__.getSetting(key).decode('utf-8')
    # アドオン設定をリセット
    __addon__.setSetting('id','')
    __addon__.setSetting('key','')
    __addon__.setSetting('s','0')
    __addon__.setSetting('day','0')
    __addon__.setSetting('ch','0')
    __addon__.setSetting('duplicate','0')
    __addon__.setSetting('name','')
    __addon__.setSetting('stream','')

    # actionに応じた処理
    if params['action'] == 'resetAll':
        resetAll()
    elif params['action'] == 'reset':
        reset()

    elif params['action'] == 'addDownload':
        result = Downloads().add(
                    id=params['id'],
                    name=params['name'],
                    start=params['start'],
                    end=params['end'],
                    title=params['title'],
                    description=params['description'],
                    options=params['options'])
        notify2(result, onlyonerror=False)
    elif params['action'] == 'showDownloads':
        Downloads().show()
    elif params['action'] == 'clearDownloads':
        result = Downloads().deleteall()
        notify2(result, onlyonerror=False)
    elif params['action'] == 'deleteDownload':
        result = Downloads().delete(params['id'])
        notify2(result)

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
    elif params['action'] == 'editKeyword':
        Keywords().edit(params['id'])
    elif params['action'] == 'editedKeyword':
        result = Keywords().edited(
            id=settings['id'],
            key=settings['key'],
            s=settings['s'],
            day=settings['day'],
            ch=settings['ch'],
            duplicate=settings['duplicate'])
        notify2(result)
    elif params['action'] == 'deleteKeyword':
        Keywords().delete(params['id'])

    # 放送局の追加、変更、削除
    elif params['action'] == 'editStation':
        Misc().edit(params['id'])
    elif params['action'] == 'editedStation':
        Misc().edited(
            settings['id'],
            settings['name'],
            settings['stream'])
        xbmc.executebuiltin('Container.Refresh()')
    elif params['action'] == 'deleteStation':
        Misc().delete(params['id'])
        xbmc.executebuiltin('Container.Refresh()')

    elif params['action'] == 'showPrograms':
        start()

    elif params['action'] == 'settings':
        xbmc.executebuiltin('Addon.OpenSettings(%s)' % __addon__.getAddonInfo('id'))

    else:
        if __addon__.getSetting('download') == 'true':
            Keywords().show()
        else:
            start()

#-------------------------------------------------------------------------------
def start(active=True):
    global Resumes
    global Birth
    # ディレクトリをチェック
    if not os.path.isdir(__cache_path__): os.makedirs(__cache_path__)
    if not os.path.isdir(__media_path__): os.makedirs(__media_path__)
    if not os.path.isdir(__data_path__):  os.makedirs(__data_path__)
    # 初期化
    if os.path.isfile(__settings_file__) and getAlive():
        data = proceed()
    else:
        data = initialize()
    # 表示
    if active: data.showPrograms()
    # Birth設定
    Birth = setBirth()
    # Alive設定を更新
    setAlive()
    # 更新
    monitor = Monitor()
    while not monitor.abortRequested():
        if monitor.waitForAbort(__check_interval__):
            log('break by aborted')
            clearResumes();
            break
        if not getBirth():
            log('break by renewed')
            break
        # __check_interval__毎に実行
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
    if auth._response['area_id'] == '': notify('Radiko authentication failed')
    # クラス初期化
    radiru = Radiru(renew=True)
    radiko = Radiko(area=auth._response['area_id'], token=auth._response['auth_token'], renew=True)
    jcba   = Jcba(renew=True)
    misc   = Misc(renew=True)
    data = Data((radiru,radiko,jcba,misc))
    # 放送局データに応じて設定画面を生成
    setup(radiru, radiko, jcba, misc)
    # 番組データを取得
    data.setPrograms(True)
    # 更新を通知
    data.onChanged()
    # Resumes設定
    (reinfo, hashinfo) = data.nextAired()
    Resumes['key'] = auth._response['partial_key']
    Resumes['token'] = auth._response['auth_token']
    Resumes['area'] = auth._response['area_id']
    Resumes['reinfo'] = reinfo
    Resumes['hashinfo'] = hashinfo
    Resumes['reauth'] = int(time.time()) + __resume_timer_interval__
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
    radiko = Radiko(Resumes['area'], Resumes['token'])
    jcba   = Jcba()
    misc   = Misc()
    data = Data((radiru,radiko,jcba,misc))
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
        data.setPrograms(True)
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
        if auth._response['area_id'] == '': notify('Radiko authentication failed')
        # Resumes設定
        Resumes['key'] = auth._response['partial_key']
        Resumes['token'] = auth._response['auth_token']
        Resumes['area'] = auth._response['area_id']
        Resumes['reauth'] = stamp + __resume_timer_interval__
        # radiko認証の更新に伴う処理
        radiru = Radiru()
        radiko = Radiko(Resumes['area'], Resumes['token'])
        jcba   = Jcba()
        misc   = Misc()
        data = Data((radiru,radiko,jcba,misc))
        # 番組データを更新
        data.setPrograms()
        # 更新を通知
        data.onChanged()
        # 画面更新
        refresh()

    # キーワードマッチによるダウンロード
    if __addon__.getSetting('download') == 'true':
        data.onWatched()

    # ダウンロードが完了している場合はRSSを更新
    if __addon__.getSetting('rss') == 'true':
        if createRSS(): notify('Download completed', image='DefaultIconInfo.png')

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
        if path == sys.argv[0] and __addon__.getSetting('download') == 'false':
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

def createRSS():
    # exitファイルをチェック
    create = False
    if os.path.isfile(__exit_file__):
        if not os.path.isfile(__rss_file__):
            create = True
        elif os.path.getmtime(__rss_file__) < os.path.getmtime(__exit_file__):
            create = True
    # RSSを生成
    if create:
        Downloads().createRSS()
    return create

#-------------------------------------------------------------------------------
if __name__  == '__main__': main()
