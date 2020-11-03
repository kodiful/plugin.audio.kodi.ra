# -*- coding: utf-8 -*-

from resources.lib.const import Const
from resources.lib.common import *

import sys, os, platform
import urlparse
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

from resources.lib.cp.misc   import Misc
from resources.lib.data      import Data
from resources.lib.downloads import Downloads
from resources.lib.keywords  import Keywords
from resources.lib.rss       import RSS

# HTTP接続におけるタイムアウト(秒)
import socket
socket.setdefaulttimeout(60)


def resetAll():
    # インストール後に生成されたプロファイルの配下のファイルをすべて削除
    for root, dirs, files in os.walk(Const.PROFILE_PATH, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
    # プロファイルディレクトリを削除
    os.rmdir(Const.PROFILE_PATH)
    # 設定ダイアログを削除
    os.remove(Const.SETTINGS_FILE)

def reset():
    # 設定ダイアログを削除
    if os.path.isfile(Const.SETTINGS_FILE):
        os.remove(Const.SETTINGS_FILE)


if __name__  == '__main__':

    # 引数
    args = urlparse.parse_qs(sys.argv[2][1:], keep_blank_values=True)
    for key in args.keys():
        args[key] = args[key][0]
    params = {'action':''}
    params.update(args)

    # ログ
    #log('path=',xbmc.getInfoLabel('Container.FolderPath'))
    #log('argv=', sys.argv)
    #log(params)

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
            ft=params['ft'],
            to=params['to'],
            title=params['title'],
            description=params['description'],
            source=params['source'],
            lag=params['lag'])
        if status:
            notify(status, error=True)
        else:
            notify('Download reserved')
    elif params['action'] == 'showDownloads':
        Downloads().show()
    elif params['action'] == 'clearDownloads':
        Downloads().deleteall()
    elif params['action'] == 'deleteDownload':
        Downloads().delete(params['id'])
    elif params['action'] == 'showContents':
        Downloads().show(params['key'])
    elif params['action'] == 'updateRSS':
        RSS().create()

    # キーワードの追加、変更、削除
    elif params['action'] == 'addKeyword':
        Keywords().add(
            key=params['title'],
            day=str(int(strptime(params['ft'],'%Y%m%d%H%M%S').strftime('%w'))+1),
            ch=params['name'])
    elif params['action'] == 'showKeywords':
        Keywords().show()
    elif params['action'] == 'beginEditKeyword':
        Keywords().beginEdit(params['id'])
    elif params['action'] == 'endEditKeyword':
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
        Data().showPrograms()
    else:
        if Const.GET('download') == 'true':
            Keywords().show()
        else:
            Data().showPrograms()
