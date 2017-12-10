# -*- coding: utf-8 -*-

import resources.lib.common as common
from common import(log,notify)

import os
import urllib, urllib2
import xml.dom.minidom
import re
import codecs
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

from bs4 import BeautifulSoup

__jcba_path__ = os.path.join(common.data_path, 'jcba')
if not os.path.isdir(__jcba_path__): os.makedirs(__jcba_path__)

__program_file__  = os.path.join(__jcba_path__, 'program.xml')
__station_file__ = os.path.join(__jcba_path__, 'station.xml')
__settings_file__ = os.path.join(__jcba_path__, 'settings.xml')

__station_url__   = 'http://kodiful.com/KodiRa/downloads/jcba/station.xml'
__settings_url__  = 'http://kodiful.com/KodiRa/downloads/jcba/settings.xml'

#-------------------------------------------------------------------------------
class Jcba:

    def __init__(self, renew=False):
        self.id = 'jcba'
        # 放送局データと設定データを初期化
        self.getStationFile(renew)

    def getStationFile(self, renew=False):
        # キャッシュがあれば何もしない
        if renew == False and os.path.isfile(__station_file__) and os.path.isfile(__settings_file__):
            return
        # 放送局データをウェブから読み込む
        response = urllib.urlopen(__station_url__)
        data = response.read().decode('utf-8')
        response.close()
        # 放送局データを書き込む
        f = codecs.open(__station_file__,'w','utf-8')
        f.write(data)
        f.close()
        # 設定データをウェブから読み込む
        response = urllib.urlopen(__settings_url__)
        data = response.read().decode('utf-8')
        response.close()
        # 設定データを書き込む
        f = codecs.open(__settings_file__,'w','utf-8')
        f.write(data)
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
            except:
                pass
        # write as xml
        f = codecs.open(__program_file__,'w','utf-8')
        f.write('<stations>' + '\n'.join(results) + '</stations>')
        f.close()
        return '\n'.join(results)
