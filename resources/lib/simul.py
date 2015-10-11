# -*- coding: utf-8 -*-

import os
import urllib, urllib2
import xml.dom.minidom
import re
import codecs

from bs4 import BeautifulSoup

from common import(__data_path__)
from common import(__settings__)

__simul_path__ = os.path.join(__data_path__, 'simul')
if not os.path.isdir(__simul_path__): os.makedirs(__simul_path__)

__program_file__  = os.path.join(__simul_path__, 'program.xml')
__station_file2__ = os.path.join(__simul_path__, 'station2.xml')
__settings_file__ = os.path.join(__simul_path__, 'settings.xml')

__station_url__   = 'http://www.kodiful.com/KodiRa/downloads/simul/station2.xml'
__settings_url__  = 'http://www.kodiful.com/KodiRa/downloads/simul/settings.xml'

#-------------------------------------------------------------------------------
class Simul:

    def __init__(self):
        self.id = 'simul'

    def getStationFile(self):
        pass

    def getStationArray(self):
        # キャッシュがある場合
        if os.path.isfile(__station_file2__):
            f = codecs.open(__station_file2__,'r','utf-8')
            data = f.read()
            f.close()
            return data
        # キャッシュがない場合
        # ファイルを読み込む
        response = urllib.urlopen(__station_url__)
        data = response.read().decode('utf-8')
        response.close()
        # ファイルを書き込む
        f = codecs.open(__station_file2__,'w','utf-8')
        f.write(data)
        f.close()
        return data

    def getSettingsArray(self):
        # キャッシュがある場合
        if os.path.isfile(__settings_file__):
            f = codecs.open(__settings_file__,'r','utf-8')
            data = f.read()
            f.close()
            return data
        # キャッシュがない場合
        # ファイルを読み込む
        response = urllib.urlopen(__settings_url__)
        data = response.read().decode('utf-8')
        response.close()
        # ファイルを書き込む
        f = codecs.open(__settings_file__,'w','utf-8')
        f.write(data)
        f.close()
        return data

    def getProgramFile(self):
        pass

    def getProgramArray(self):
        f = codecs.open(__station_file2__,'r','utf-8')
        xmlstr = f.read()
        f.close()
        results = []
        stations = BeautifulSoup('<stations>%s</stations>' % xmlstr).find_all('station')
        for station in stations:
            try:
                id = station.find('id').string
                onair = station.find('onair').string
                if onair is None: onair = ''
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
