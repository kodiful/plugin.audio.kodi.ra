# -*- coding: utf-8 -*-

# HTTP接続のタイムアウト(秒)を設定
import socket
socket.setdefaulttimeout(60)

# extディレクトリをパスに追加
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'resources', 'ext'))

from resources.lib.const import *
from resources.lib.common import *
from resources.lib.cp import Misc
from resources.lib.programs import Programs
from resources.lib.downloads import Downloads
from resources.lib.keywords import Keywords
from resources.lib.contents import Contents

from service import Service

import urlparse
import xbmc, xbmcgui, xbmcplugin, xbmcaddon


class Cache(Service):

    def __init__(self):
        return

    def update(self, renew=False):
        # radiko認証情報を更新
        self.authenticate()
        # クラスを更新
        self.update_classes(renew)
        # 設定ダイアログを更新
        self.setup_settings()

    def __clear(self, dirpath):
        for root, dirs, files in os.walk(dirpath, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))

    def resetAll(self):
        # インストール後に生成されたプロファイルの配下のファイルをすべて削除
        self.__clear(Const.PROFILE_PATH)
        # 設定ダイアログを削除
        os.remove(Const.SETTINGS_FILE)
        # 初期化
        self.update()

    def clearAll(self):
        # すべてのキャッシュを削除
        self.__clear(Const.CACHE_PATH)
        # 初期化
        self.update()

    def clearMedia(self):
        # メディアキャッシュを削除
        self.__clear(Const.MEDIA_PATH)
        # 初期化
        self.update()

    def clearData(self):
        # データキャッシュを削除
        self.__clear(Const.DATA_PATH)
        # 初期化
        self.update()


if __name__  == '__main__':

    # 引数
    args = urlparse.parse_qs(sys.argv[2][1:], keep_blank_values=True)
    for key in args.keys():
        args[key] = args[key][0]

    # action
    action = args.get('action')
    if action:
        pass
    elif Const.GET('download') == 'true':
        action = 'showKeywords'
    else:
        action = 'showPrograms'

    # ログ
    #log('path=',xbmc.getInfoLabel('Container.FolderPath'))
    #log('argv=',sys.argv)
    #log(args)

    # アドオン設定をコピー
    settings = {}
    for key in ['id','key','s','day','ch','duplicate','name','stream','logo']:
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
    Const.SET('logo','')

    # actionに応じた処理

    # リセット
    if action == 'resetAll':
        notify('Initializing settings...')
        Cache().resetAll()
        xbmc.executebuiltin("Container.Refresh")
    elif action == 'clearAll':
        notify('Clearing cached data and images...')
        Cache().clearAll()
        xbmc.executebuiltin("Container.Refresh")
    elif action == 'clearMedia':
        notify('Clearing cached images...')
        Cache().clearMedia()
        xbmc.executebuiltin("Container.Refresh")
    elif action == 'clearData':
        notify('Clearing cached data...')
        Cache().clearData()
        xbmc.executebuiltin("Container.Refresh")
    elif action == 'updateDialog':
        Cache().update()
        xbmc.executebuiltin("Container.Refresh")

    # ダウンロードの管理
    elif action == 'enqueueDownload':
        status = Downloads().enqueue(
            id=args['id'],
            name=args['name'],
            ft=args['ft'],
            to=args['to'],
            title=args['title'],
            description=args['description'],
            stream=args['stream'],
            url=args['url'],
            delay=args['delay'])
        if status:
            notify(status, error=True)
        else:
            notify('Download enqueued')
    elif action == 'deleteDownload':
        Contents().delete(gtvid=args['id'])
        xbmc.executebuiltin('Container.Refresh()')
    elif action == 'clearDownloads':
        if xbmcgui.Dialog().yesno(Const.ADDON_NAME, Const.STR(30800)):
            Contents().delete()
            xbmc.executebuiltin('Container.Refresh()')

    # キーワードの追加、変更、削除
    elif action == 'addKeyword':
        Keywords().beginEdit(
            key=args['title'],
            day=str(int(strptime(args['ft'],'%Y%m%d%H%M%S').strftime('%w'))+1),
            ch=args['name'])
    elif action == 'beginEditKeyword':
        Keywords().beginEdit(id=args['id'])
    elif action == 'endEditKeyword':
        Keywords().endEdit(
            id=settings['id'],
            key=settings['key'],
            s=settings['s'],
            day=settings['day'],
            ch=settings['ch'],
            duplicate=settings['duplicate'])
        xbmc.executebuiltin("Container.Refresh")
    elif action == 'deleteKeyword':
        Keywords().delete(args['id'])
        xbmc.executebuiltin("Container.Refresh")

    # 放送局の追加、変更、削除
    elif action == 'beginEditStation':
        Misc().beginEdit(args['id'])
    elif action == 'endEditStation':
        Misc().endEdit(
            settings['id'],
            settings['name'],
            settings['stream'],
            settings['logo'])
        xbmc.executebuiltin('Container.Refresh()')
    elif action == 'deleteStation':
        if Misc().delete(args['id']) > -1:
            xbmc.executebuiltin('Container.Refresh()')

    # アドオン設定
    elif action == 'settings':
        Const.SET('id','')
        Const.SET('key','')
        Const.SET('s','0')
        Const.SET('day','0')
        Const.SET('ch','0')
        Const.SET('duplicate','0')
        Const.SET('name','')
        Const.SET('stream','')
        xbmc.executebuiltin('Addon.OpenSettings(%s)' % Const.ADDON_ID)

    # RSS
    elif action == 'updateRSS':
        Contents(args['key']).createrss()

    # 表示
    elif action == 'showContents':
        Contents(args['key']).show()
    elif action == 'showKeywords':
        Keywords().show()
    elif action == 'showPrograms':
        Programs().show()
    elif action == 'updatePrograms':
        Cache().update(renew=True)
        Programs().show()

    # 未定義
    else:
        log('undefined action:', action)
