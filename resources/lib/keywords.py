# -*- coding: utf-8 -*-

import os, sys
import json
import re
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

from resources.lib.common import(
    __addon__,
    __keywords_file__)

class Keywords:

    def __init__(self):
        self.read()

    def read(self):
        if os.path.isfile(__keywords_file__):
            f = open(__keywords_file__,'r')
            self.search = json.loads(f.read(), 'utf-8')
            f.close()
        else:
            self.search = []

    def write(self):
        f = open(__keywords_file__,'w')
        f.write(json.dumps(self.search, sort_keys=True, ensure_ascii=False, indent=2).encode('utf-8'))
        f.close()

    def show(self):
        # すべて表示
        if __addon__.getSetting('download') == 'true':
            # 放送中の番組
            li = xbmcgui.ListItem(__addon__.getLocalizedString(30316), iconImage='DefaultFolder.png', thumbnailImage='DefaultFolder.png')
            # アドオン設定
            contextmenu = []
            contextmenu.append((__addon__.getLocalizedString(30051), 'RunPlugin(%s?action=settings)' % (sys.argv[0])))
            li.addContextMenuItems(contextmenu, replaceItems=True)
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), '%s?action=showPrograms' % (sys.argv[0]), listitem=li, isFolder=True, totalItems=len(self.search)+2)
            # すべての保存済み番組
            li = xbmcgui.ListItem(__addon__.getLocalizedString(30317), iconImage='DefaultFolder.png', thumbnailImage='DefaultFolder.png')
            # アドオン設定
            contextmenu = []
            contextmenu.append((__addon__.getLocalizedString(30051), 'RunPlugin(%s?action=settings)' % (sys.argv[0])))
            li.addContextMenuItems(contextmenu, replaceItems=True)
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), '%s?action=showContents&key=' % (sys.argv[0]), listitem=li, isFolder=True, totalItems=len(self.search)+2)
        # キーワードを表示
        id = 0
        for s in self.search:
            # listitemを追加
            li = xbmcgui.ListItem(s['key'], iconImage='DefaultFolder.png', thumbnailImage='DefaultPlaylist.png')
            # context menu
            contextmenu = []
            contextmenu.append((__addon__.getLocalizedString(30315), 'RunPlugin(%s?action=editKeyword&id=%d)' % (sys.argv[0],id)))
            contextmenu.append((__addon__.getLocalizedString(30314), 'RunPlugin(%s?action=deleteKeyword&id=%d)' % (sys.argv[0],id)))
            li.addContextMenuItems(contextmenu, replaceItems=True)
            # add directory item
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), '%s?action=showContents&key=%s' % (sys.argv[0],s['key']), li, isFolder=True, totalItems=len(self.search)+1)
            id = id+1
        xbmcplugin.endOfDirectory(int(sys.argv[1]), succeeded=True)

    def add(self, key, s='0', day='0', ch='0', duplicate='false'):
        __addon__.setSetting('id','')
        __addon__.setSetting('key',key)
        __addon__.setSetting('s',s)
        __addon__.setSetting('day',day)
        __addon__.setSetting('ch',ch)
        __addon__.setSetting('duplicate',duplicate)
        xbmc.executebuiltin('Addon.OpenSettings(%s)' % __addon__.getAddonInfo('id'))
        xbmc.executebuiltin('SetFocus(105)') # select 6th category
        xbmc.executebuiltin('SetFocus(204)') # select 5th control

    def edit(self, id):
        elem = self.search[int(id)]
        __addon__.setSetting('id',str(id))
        __addon__.setSetting('key',elem['key'])
        __addon__.setSetting('s',elem['s'])
        __addon__.setSetting('day',elem['day'])
        __addon__.setSetting('ch',elem['ch'])
        __addon__.setSetting('duplicate',elem['duplicate'])
        xbmc.executebuiltin('Addon.OpenSettings(%s)' % __addon__.getAddonInfo('id'))
        xbmc.executebuiltin('SetFocus(105)') # select 6th category
        xbmc.executebuiltin('SetFocus(204)') # select 5th control

    def edited(self, id, key, s, day, ch, duplicate):
        key = re.sub(r'(^\s+|\s+$)','',key)
        if id=='':
            for elem in self.search:
                if elem['key'] == key:
                    return {'status':False, 'message':'Failed. Keyword exists'}
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
                        return {'status':False, 'message':'Failed. Keyword exists'}
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
        return {'status':True, 'message':'Keyword added/changed successfully'}

    def delete(self, id):
        if int(id) < len(self.search):
            # id番目の要素を削除
            self.search.pop(int(id))
            # 変更した設定を書き込む
            self.write()
            # 再表示
            xbmc.executebuiltin("Container.Refresh")
