# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import datetime, time
import os, sys, glob, shutil
import codecs
import json
import re
import urllib2
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

from datetime import datetime

from resources.lib.common import(
    __addon_id__,
    __settings__,
    __plugin_path__,
    __template_path__)

from resources.lib.common import(
    __keywords_file__)

class Keywords:

    def __init__(self):
        if os.path.isfile(__keywords_file__):
            f = codecs.open(__keywords_file__,'r','utf-8')
            self.search = json.loads(f.read())
            f.close()
        else:
            self.search = []

    def show(self):
        # すべて表示
        if __settings__.getSetting('download') == 'true':
            li = xbmcgui.ListItem(__settings__.getLocalizedString(30316), iconImage='DefaultFolder.png', thumbnailImage='DefaultFolder.png')
            # コンテクストメニュー
            contextmenu = []
            #contextmenu.append((__settings__.getLocalizedString(30055), 'XBMC.Container.Refresh'))
            li.addContextMenuItems(contextmenu, replaceItems=True)
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), '%s?action=showContents&key=' % (sys.argv[0]), listitem=li, isFolder=True, totalItems=len(self.search)+1)
        # キーワードを表示
        id = 0
        for s in self.search:
            # listitemを追加
            li = xbmcgui.ListItem(s['key'], iconImage='DefaultFolder.png', thumbnailImage='DefaultFolder.png')
            # context menu
            contextmenu = []
            contextmenu.append((__settings__.getLocalizedString(30315), 'XBMC.RunPlugin(%s?action=editKeyword&id=%d)' % (sys.argv[0],id)))
            contextmenu.append((__settings__.getLocalizedString(30314), 'XBMC.RunPlugin(%s?action=deleteKeyword&id=%d)' % (sys.argv[0],id)))
            li.addContextMenuItems(contextmenu, replaceItems=True)
            # add directory item
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), '%s?action=showContents&key=%s' % (sys.argv[0],s['key']), li, isFolder=True, totalItems=len(self.search)+1)
            id = id+1
        xbmcplugin.endOfDirectory(int(sys.argv[1]), succeeded=True)

    def add(self, key, s='0', day='0', ch='0', duplicate='false'):
        __settings__.setSetting('id','')
        __settings__.setSetting('key',key)
        __settings__.setSetting('s',s)
        __settings__.setSetting('day',day)
        __settings__.setSetting('ch',ch)
        __settings__.setSetting('duplicate',duplicate)
        xbmc.executebuiltin('Addon.OpenSettings(%s)' % __addon_id__)
        xbmc.executebuiltin('SetFocus(104)') # select 5th category
        xbmc.executebuiltin('SetFocus(204)') # select 5th control

    def edit(self, id):
        elem = self.search[int(id)]
        __settings__.setSetting('id',str(id))
        __settings__.setSetting('key',elem['key'])
        __settings__.setSetting('s',elem['s'])
        __settings__.setSetting('day',elem['day'])
        __settings__.setSetting('ch',elem['ch'])
        __settings__.setSetting('duplicate',elem['duplicate'])
        xbmc.executebuiltin('Addon.OpenSettings(%s)' % __addon_id__)
        xbmc.executebuiltin('SetFocus(104)') # select 5th category
        xbmc.executebuiltin('SetFocus(204)') # select 5th control

    def edited(self):
        key = re.sub(r'(^\s+|\s+$)','', __settings__.getSetting('key'))
        id = __settings__.getSetting('id')
        if id=='':
            for elem in self.search:
                if elem['key'] == key.decode('utf-8'):
                    return {'status':False, 'message':'Failed. Keyword exists'}
            elem = {}
            elem['key'] = key.decode('utf-8')
            elem['s'] = __settings__.getSetting('s')
            elem['day'] = __settings__.getSetting('day')
            elem['ch'] = __settings__.getSetting('ch')
            elem['duplicate'] = __settings__.getSetting('duplicate')
            self.search.append(elem)
            # キーワードを表示
            xbmc.executebuiltin("XBMC.Container.Update(%s?action=showKeywords)" % (sys.argv[0]))
        else:
            if self.search[int(id)]['key'] == key.decode('utf-8'):
                pass
            else:
                for elem in self.search:
                    if elem['key'] == key.decode('utf-8'):
                        return {'status':False, 'message':'Failed. Keyword exists'}
            elem = self.search[int(id)]
            elem['key'] = key.decode('utf-8')
            elem['s'] = __settings__.getSetting('s')
            elem['day'] = __settings__.getSetting('day')
            elem['ch'] = __settings__.getSetting('ch')
            elem['duplicate'] = __settings__.getSetting('duplicate')
            # 再表示
            xbmc.executebuiltin("XBMC.Container.Refresh")
        # キーワード順にソート
        self.search = sorted(self.search, key=lambda item: item['key'])
        # 変更した設定を書き込む
        f = codecs.open(__keywords_file__,'w','utf-8')
        f.write(json.dumps(self.search))
        f.close()
        # リセット
        self.reset()
        return {'status':True, 'message':'Keyword added/changed successfully'}

    def reset(self):
        __settings__.setSetting('id','')
        __settings__.setSetting('key','')
        __settings__.setSetting('s','0')
        __settings__.setSetting('day','0')
        __settings__.setSetting('ch','0')
        __settings__.setSetting('duplicate','0')
        
    def delete(self, id):
        elem = self.search[int(id)]
        search = []
        for s in self.search:
            if s == elem:
                pass
            else:
                search.append(s)
        self.search = search
        # 変更した設定を書き込む
        f = codecs.open(__keywords_file__,'w','utf-8')
        f.write(json.dumps(self.search))
        f.close()
        # 再表示
        xbmc.executebuiltin("XBMC.Container.Refresh")
