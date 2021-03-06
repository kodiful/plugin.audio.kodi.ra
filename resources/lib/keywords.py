# -*- coding: utf-8 -*-

from .const import Const
from .common import *

import os
import sys
import json
import re
import glob
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

from downloads import Downloads


class Keywords:

    def __init__(self):
        self.read()

    def read(self):
        self.keywords = read_json(Const.KEYWORDS_FILE) or []

    def write(self):
        write_json(Const.KEYWORDS_FILE, self.keywords)

    def show(self):
        # 放送中の番組
        li = xbmcgui.ListItem(Const.STR(30316), iconImage='DefaultFolder.png', thumbnailImage='DefaultFolder.png')
        # アドオン設定
        contextmenu = []
        contextmenu.append((Const.STR(30051), 'RunPlugin(%s?action=settings)' % sys.argv[0]))
        li.addContextMenuItems(contextmenu, replaceItems=True)
        xbmcplugin.addDirectoryItem(int(sys.argv[1]), '%s?action=showPrograms' % sys.argv[0], listitem=li, isFolder=True)
        # すべての保存済み番組
        li = xbmcgui.ListItem(Const.STR(30317), iconImage='DefaultFolder.png', thumbnailImage='DefaultFolder.png')
        # アドオン設定
        contextmenu = []
        contextmenu.append((Const.STR(30051), 'RunPlugin(%s?action=settings)' % sys.argv[0]))
        li.addContextMenuItems(contextmenu, replaceItems=True)
        xbmcplugin.addDirectoryItem(int(sys.argv[1]), '%s?action=showContents&key=' % sys.argv[0], listitem=li, isFolder=True)
        # キーワードを表示
        for i, s in enumerate(self.keywords):
            # listitemを追加
            li = xbmcgui.ListItem(s['key'], iconImage='DefaultFolder.png', thumbnailImage='DefaultPlaylist.png')
            # context menu
            contextmenu = []
            contextmenu.append((Const.STR(30320), 'RunPlugin(%s?action=beginEditKeyword&id=%d)' % (sys.argv[0],i)))
            #contextmenu.append((Const.STR(30321), 'RunPlugin(%s?action=deleteKeyword&id=%d&level=1)' % (sys.argv[0],i)))
            contextmenu.append((Const.STR(30322), 'RunPlugin(%s?action=deleteKeyword&id=%d&level=2)' % (sys.argv[0],i)))
            contextmenu.append((Const.STR(30323), 'RunPlugin(%s?action=deleteKeyword&id=%d&level=3)' % (sys.argv[0],i)))
            contextmenu.append((Const.STR(30051), 'RunPlugin(%s?action=settings)' % sys.argv[0]))
            li.addContextMenuItems(contextmenu, replaceItems=True)
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), '%s?action=showContents&key=%s' % (sys.argv[0],s['key']), listitem=li, isFolder=True)
        xbmcplugin.endOfDirectory(int(sys.argv[1]), succeeded=True)

    def beginEdit(self, id='', key='', s='0', day='0', ch='0', duplicate='false'):
        elem = self.keywords[int(id)] if id else {}
        Const.SET('id', id)
        Const.SET('key', elem.get('key',key))
        Const.SET('s', elem.get('s',s))
        Const.SET('day', elem.get('day',day))
        Const.SET('ch', elem.get('ch',ch))
        Const.SET('duplicate', elem.get('duplicate',duplicate))
        Const.SET('name','')
        Const.SET('stream','')
        xbmc.executebuiltin('Addon.OpenSettings(%s)' % Const.ADDON_ID)
        xbmc.executebuiltin('SetFocus(105)') # select 6th category
        xbmc.executebuiltin('SetFocus(204)') # select 5th control

    def endEdit(self, id, key, s, day, ch, duplicate):
        key = re.sub(r'(^\s+|\s+$)', '', key)
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
        # キーワード順にソート
        self.keywords = sorted(self.keywords, key=lambda item: item['key'])
        # 変更した設定を書き込む
        self.write()

    def delete(self, id, level):
        # ファイルを削除する
        if int(level) & 2:
            # id番目のキーワードのファイルを削除
            key = self.keywords[int(id)]
            Downloads().delete(key=key['key'])
        # キーワードを削除する
        if int(level) & 1:
            # id番目の要素を削除
            self.keywords.pop(int(id))
            # 変更した設定を書き込む
            self.write()

    def match(self, p):
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
            # ダウンロードフォルダで対応するmp3ファイルが存在するjsonファイルを抽出する
            files = filter(
                lambda file: os.path.isfile(os.path.join(Const.DOWNLOAD_PATH, file.replace('.json','.mp3'))),
                glob.glob(os.path.join(Const.DOWNLOAD_PATH, '*.json')))
            # jsonファイルの内容をチェック
            for file in files:
                program = read_json(file)
                if p['name'] == program['name']:
                    if k['s'] == '0' and p['title'] == program['title']:
                        # 番組名が一致する
                        return False
                    if k['s'] == '1' and p['title'] == program['title'] and p['description'] == program['description']:
                        # 番組名と詳細情報が一致する
                        return False
        return True
