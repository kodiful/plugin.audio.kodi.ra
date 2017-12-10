# -*- coding: utf-8 -*-

import resources.lib.common as common
from common import(log,notify)

import os, sys
import urllib, urllib2
import xml.dom.minidom
import re
import codecs
import json
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

from bs4 import BeautifulSoup

__misc_path__ = os.path.join(common.data_path, 'misc')
if not os.path.isdir(__misc_path__): os.makedirs(__misc_path__)

__program_file__  = os.path.join(__misc_path__, 'program.xml')
__station_file__ = os.path.join(__misc_path__, 'station.xml')
__settings_file__ = os.path.join(__misc_path__, 'settings.xml')

#-------------------------------------------------------------------------------
class Misc:

    def __init__(self, renew=False):
        self.id = 'misc'
        # 放送局データをファイルから読み込む
        self.read()
        # 放送局データと設定データを初期化
        self.getStationFile(renew)

    def read(self):
        if os.path.isfile(common.channels_file):
            f = open(common.channels_file,'r')
            self.ch = json.loads(f.read(), 'utf-8')
            f.close()
        else:
            self.ch = []

    def write(self):
        f = open(common.channels_file,'w')
        f.write(json.dumps(self.ch, sort_keys=True, ensure_ascii=False, indent=2).encode('utf-8'))
        f.close()

    def getStationFile(self, renew=False):
        # キャッシュがあれば何もしない
        if renew == False and os.path.isfile(__station_file__) and os.path.isfile(__settings_file__):
            return
        # データ変換
        results = []
        settings = []
        id = 1
        for ch in self.ch:
            name = ch['name']
            logo = ''
            url = ch['stream']
            options = ''
            # pack as xml
            xmlstr = '<station>'
            xmlstr += '<id>misc_%03d</id>' % (id)
            xmlstr += '<name>%s</name>' % (name)
            xmlstr += '<logo_large>%s</logo_large>' % (logo)
            xmlstr += '<url>%s</url>' % (url)
            xmlstr += '<options>%s</options>' % (options)
            xmlstr += '</station>'
            results.append(xmlstr)
            # pack as xml (for settings)
            xmlstr = '<setting label="%s" type="bool" id="misc_%03d" default="true" enable="eq(%d,2)" visible="true"/>' % (name,id,-id)
            settings.append(xmlstr)
            id = id + 1
        # 放送局データを書き込む
        f = codecs.open(__station_file__,'w','utf-8')
        f.write('\n'.join(results))
        f.close()
        # 設定データを書き込む
        f = codecs.open(__settings_file__,'w','utf-8')
        f.write('\n'.join(settings))
        f.close()

    def getStationData(self):
        f = codecs.open(__station_file__,'r','utf-8')
        data = f.read()
        f.close()
        return data

    def getSettingsData(self):
        f = codecs.open(__settings_file__,'r','utf-8')
        data = f.read()
        f.close()
        return data

    def getProgramFile(self):
        return

    def getProgramData(self, renew=False):
        f = codecs.open(__station_file__,'r','utf-8')
        xmlstr = f.read()
        f.close()
        results = []
        stations = BeautifulSoup('<stations>%s</stations>' % xmlstr, 'html.parser').find_all('station')
        for station in stations:
            try:
                id = station.find('id').string
                onair = station.find('onair')
                if onair:
                    onair = onair.get_text()
                else:
                    onair = ''
                xmlstr = '<station id="%s">' % (id)
                xmlstr += '<prog>'
                xmlstr += '<title>%s</title>' % (onair)
                xmlstr += '</prog>'
                xmlstr += '</station>'
                results.append(xmlstr)
            except Exception as e:
                pass
        # write as xml
        f = codecs.open(__program_file__,'w','utf-8')
        f.write('<stations>' + '\n'.join(results) + '</stations>')
        f.close()
        return '\n'.join(results)

    def edit(self, id):
        ch = self.ch[int(id)]
        common.addon.setSetting('id',str(id))
        common.addon.setSetting('name',ch['name'])
        common.addon.setSetting('stream',ch['stream'])
        xbmc.executebuiltin('Addon.OpenSettings(%s)' % common.addon.getAddonInfo('id'))
        xbmc.executebuiltin('SetFocus(103)') # select 4th category
        xbmc.executebuiltin('SetFocus(201)') # select 2nd control

    def edited(self, id, name, stream):
        if name and stream:
            if id == '':
                self.ch.append({'name':name, 'stream':stream})
            elif int(id) < len(self.ch):
                self.ch[int(id)]['name'] = name
                self.ch[int(id)]['stream'] = stream
            else:
                return
            # 追加/編集した設定を書き込む
            self.write()
            # 変更を反映する
            self.getStationFile(renew=True)
            xbmc.executebuiltin('RunPlugin(%s?action=reset)' % (sys.argv[0]))

    def delete(self, id):
        if int(id) < len(self.ch):
            # id番目の要素を削除
            self.ch.pop(int(id))
            # 削除した設定を書き込む
            self.write()
            # 変更を反映する
            self.getStationFile(renew=True)
            xbmc.executebuiltin('RunPlugin(%s?action=reset)' % (sys.argv[0]))
