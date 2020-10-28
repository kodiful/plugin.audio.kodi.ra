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
        self.search = read_json(Const.KEYWORDS_FILE) or []

    def write(self):
        write_json(Const.KEYWORDS_FILE, self.search)

    def show(self):
        # すべて表示
        if Const.GET('download') == 'true':
            # 放送中の番組
            li = xbmcgui.ListItem(Const.STR(30316), iconImage='DefaultFolder.png', thumbnailImage='DefaultFolder.png')
            # アドオン設定
            contextmenu = []
            contextmenu.append((Const.STR(30051), 'RunPlugin(%s?action=settings)' % (sys.argv[0])))
            li.addContextMenuItems(contextmenu, replaceItems=True)
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), '%s?action=showPrograms' % (sys.argv[0]), listitem=li, isFolder=True, totalItems=len(self.search)+2)
            # すべての保存済み番組
            li = xbmcgui.ListItem(Const.STR(30317), iconImage='DefaultFolder.png', thumbnailImage='DefaultFolder.png')
            # アドオン設定
            contextmenu = []
            contextmenu.append((Const.STR(30051), 'RunPlugin(%s?action=settings)' % (sys.argv[0])))
            li.addContextMenuItems(contextmenu, replaceItems=True)
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), '%s?action=showContents&key=' % (sys.argv[0]), listitem=li, isFolder=True, totalItems=len(self.search)+2)
        # キーワードを表示
        id = 0
        for s in self.search:
            # listitemを追加
            li = xbmcgui.ListItem(s['key'], iconImage='DefaultFolder.png', thumbnailImage='DefaultPlaylist.png')
            # context menu
            contextmenu = []
            contextmenu.append((Const.STR(30321), 'RunPlugin(%s?action=editKeyword&id=%d)' % (sys.argv[0],id)))
            contextmenu.append((Const.STR(30320), 'RunPlugin(%s?action=deleteKeyword&id=%d)' % (sys.argv[0],id)))
            contextmenu.append((Const.STR(30051), 'RunPlugin(%s?action=settings)' % (sys.argv[0])))
            li.addContextMenuItems(contextmenu, replaceItems=True)
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), '%s?action=showContents&key=%s' % (sys.argv[0],s['key']), listitem=li, isFolder=True, totalItems=len(self.search)+2)
            id = id+1
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

    def edit(self, id):
        elem = self.search[int(id)]
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

    def edited(self, id, key, s, day, ch, duplicate):
        key = re.sub(r'(^\s+|\s+$)','',key)
        if id=='':
            for elem in self.search:
                if elem['key'] == key:
                    notify('Keyword edit failed (Keyword exists)', error=True)
                    return
            elem = {}
            elem['key'] = key
            elem['s'] = s
            elem['day'] = day
            elem['ch'] = ch
            elem['duplicate'] = duplicate
            self.search.append(elem)
            # キーワードを表示
            xbmc.executebuiltin("Container.Update(%s?action=showKeywords)" % (sys.argv[0]))
        else:
            if self.search[int(id)]['key'] == key:
                pass
            else:
                for elem in self.search:
                    if elem['key'] == key:
                        notify('Keyword edit failed (Keyword exists)', error=True)
                        return
            elem = self.search[int(id)]
            elem['key'] = key
            elem['s'] = s
            elem['day'] = day
            elem['ch'] = ch
            elem['duplicate'] = duplicate
            # 再表示
            xbmc.executebuiltin("Container.Refresh")
        # キーワード順にソート
        self.search = sorted(self.search, key=lambda item: item['key'])
        # 変更した設定を書き込む
        self.write()

    def delete(self, id):
        if int(id) < len(self.search):
            # id番目の要素を削除
            self.search.pop(int(id))
            # 変更した設定を書き込む
            self.write()
            # 再表示
            xbmc.executebuiltin("Container.Refresh")
