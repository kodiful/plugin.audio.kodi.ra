# -*- coding: utf-8 -*-

from .const import Const
from .common import *

import os, sys
import json
import re
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

class Keywords:

    def __init__(self):
        self.read()

    def read(self):
        self.keywords = read_json(Const.KEYWORDS_FILE) or []

    def write(self):
        write_json(Const.KEYWORDS_FILE, self.keywords)

    def show(self):
        # すべて表示
        if Const.GET('download') == 'true':
            # 放送中の番組
            li = xbmcgui.ListItem(Const.STR(30316), iconImage='DefaultFolder.png', thumbnailImage='DefaultFolder.png')
            # アドオン設定
            contextmenu = []
            contextmenu.append((Const.STR(30051), 'RunPlugin(%s?action=settings)' % (sys.argv[0])))
            li.addContextMenuItems(contextmenu, replaceItems=True)
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), '%s?action=showPrograms' % (sys.argv[0]), listitem=li, isFolder=True)
            # すべての保存済み番組
            li = xbmcgui.ListItem(Const.STR(30317), iconImage='DefaultFolder.png', thumbnailImage='DefaultFolder.png')
            # アドオン設定
            contextmenu = []
            contextmenu.append((Const.STR(30051), 'RunPlugin(%s?action=settings)' % (sys.argv[0])))
            li.addContextMenuItems(contextmenu, replaceItems=True)
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), '%s?action=showContents&key=' % (sys.argv[0]), listitem=li, isFolder=True)
        # キーワードを表示
        for i, s in enumerate(self.keywords):
            # listitemを追加
            li = xbmcgui.ListItem(s['key'], iconImage='DefaultFolder.png', thumbnailImage='DefaultPlaylist.png')
            # context menu
            contextmenu = []
            contextmenu.append((Const.STR(30321), 'RunPlugin(%s?action=beginEditKeyword&id=%d)' % (sys.argv[0],i)))
            contextmenu.append((Const.STR(30320), 'RunPlugin(%s?action=deleteKeyword&id=%d)' % (sys.argv[0],i)))
            contextmenu.append((Const.STR(30051), 'RunPlugin(%s?action=settings)' % (sys.argv[0])))
            li.addContextMenuItems(contextmenu, replaceItems=True)
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), '%s?action=showContents&key=%s' % (sys.argv[0],s['key']), listitem=li, isFolder=True)
        xbmcplugin.endOfDirectory(int(sys.argv[1]), succeeded=True)

    def add(self, key, s='0', day='0', ch='0', duplicate='false'):
        Const.SET('id','')
        Const.SET('key',key)
        Const.SET('s',s)
        Const.SET('day',day)
        Const.SET('ch',ch)
        Const.SET('duplicate',duplicate)
        Const.SET('name','')
        Const.SET('stream','')
        xbmc.executebuiltin('Addon.OpenSettings(%s)' % Const.ADDON_ID)
        xbmc.executebuiltin('SetFocus(105)') # select 6th category
        xbmc.executebuiltin('SetFocus(204)') # select 5th control

    def beginEdit(self, id):
        elem = self.keywords[int(id)]
        Const.SET('id',str(id))
        Const.SET('key',elem['key'])
        Const.SET('s',elem['s'])
        Const.SET('day',elem['day'])
        Const.SET('ch',elem['ch'])
        Const.SET('duplicate',elem['duplicate'])
        Const.SET('name','')
        Const.SET('stream','')
        xbmc.executebuiltin('Addon.OpenSettings(%s)' % Const.ADDON_ID)
        xbmc.executebuiltin('SetFocus(105)') # select 6th category
        xbmc.executebuiltin('SetFocus(204)') # select 5th control

    def endEdit(self, id, key, s, day, ch, duplicate):
        key = re.sub(r'(^\s+|\s+$)','',key)
        if id=='':
            for elem in self.keywords:
                if elem['key'] == key:
                    notify('Keyword edit failed (Keyword exists)', error=True)
                    return
            elem = {}
            elem['key'] = key
            elem['s'] = s
            elem['day'] = day
            elem['ch'] = ch
            elem['duplicate'] = duplicate
            self.keywords.append(elem)
            # キーワードを表示
            xbmc.executebuiltin("Container.Update(%s?action=showKeywords)" % (sys.argv[0]))
        else:
            if self.keywords[int(id)]['key'] == key:
                pass
            else:
                for elem in self.keywords:
                    if elem['key'] == key:
                        notify('Keyword edit failed (Keyword exists)', error=True)
                        return
            elem = self.keywords[int(id)]
            elem['key'] = key
            elem['s'] = s
            elem['day'] = day
            elem['ch'] = ch
            elem['duplicate'] = duplicate
            # 再表示
            xbmc.executebuiltin("Container.Refresh")
        # キーワード順にソート
        self.keywords = sorted(self.keywords, key=lambda item: item['key'])
        # 変更した設定を書き込む
        self.write()

    def delete(self, id):
        if int(id) < len(self.keywords):
            # id番目の要素を削除
            self.keywords.pop(int(id))
            # 変更した設定を書き込む
            self.write()
            # 再表示
            xbmc.executebuiltin("Container.Refresh")

    def matchProgram(self, p):
        for k in self.keywords:
            # キーワードを照合
            if self.__match_keyword(k, p) == False: continue
            # 曜日を照合
            if self.__match_day(k, p) == False: continue
            # 放送局を照合
            if self.__match_station(k, p) == False: continue
            # 重複をチェック
            if self.__match_duplicate(k, p) == False: continue
            # すべてクリアしたキーワードを返す
            return k

    def __match_keyword(self, k, p):
        if k['key']:
            if p['title'].find(k['key']) > -1:
                return True
            elif k['s'] == '1' and p['description'].find(k['key']) > -1:
                return True
        return False

    def __match_day(self, k, p):
        if k['day'] == '0':
            return True
        elif int(strptime(p['ft'],'%Y%m%d%H%M%S').strftime('%w')) == int(k['day'])-1:
            return True
        return False

    def __match_station(self, k, p):
        if k['ch'] == Const.STR(30520):
            return True
        elif k['ch'] == p['name']:
            return True
        return False

    def __match_duplicate(self, k, p):
        if k['duplicate'] == '1':
            # ダウンロードフォルダで対応するmp3ファイルが存在するjsファイルを抽出する
            files = filter(
                lambda file: os.path.isfile(os.path.join(Const.DOWNLOAD_PATH, file.replace('.js','.mp3'))),
                glob.glob(os.path.join(Const.DOWNLOAD_PATH, '*.js')))
            # jsファイルの内容をチェック
            for file in files:
                program = read_json(file)['program'][0]
                if p['name'] == program['bc']:
                    if k['s'] == '0' and p['title'] == program['title']:
                        # 番組名が一致する
                        return False
                    if k['s'] == '1' and p['title'] == program['title'] and p['description'] == program['description']:
                        # 番組名と詳細情報が一致する
                        return False
        return True
