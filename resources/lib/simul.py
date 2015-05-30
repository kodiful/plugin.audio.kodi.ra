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
__station_file__  = os.path.join(__simul_path__, 'station.xml')
__station_file2__ = os.path.join(__simul_path__, 'station2.xml')
__settings_file__ = os.path.join(__simul_path__, 'settings.xml')

__station_url__   = 'http://csra.fm/stationlist/'
__service_url__   = 'http://csra.fm'


#-------------------------------------------------------------------------------
class Simul:

    def __init__(self):
        self.id = 'simul'
    
    def getStationFile(self):
        # キャッシュがある場合
        if os.path.isfile(__station_file__):
            return
        # キャッシュがない場合
        response = urllib.urlopen(__station_url__)
        data = response.read()
        response.close()
        # ファイルを書き込む
        f = codecs.open(__station_file__,'w','utf-8')
        f.write(data.decode('utf-8').replace('</?php>','</html>'))
        f.close()

    def getStationArray(self):
        # キャッシュがある場合
        if os.path.isfile(__station_file2__):
            f = codecs.open(__station_file2__,'r','utf-8')
            data = f.read()
            f.close()
            return data
        # キャッシュがない場合
        xmlstr = open(__station_file__, 'r').read()
        results = []
        settings = []
        i = -1
        sections = BeautifulSoup(xmlstr).find_all('section')
        for section in sections:
            try:
                # parse html
                stlist = section.find('a', class_='stationlist')
                name = stlist.find('h1').string
                place = stlist.find('p').string
                id = stlist.get('href').replace('/blog/author/','').replace('/','')
                logo = stlist.find('img').get('src')
                onair = stlist.get('title')
                onair = re.sub(r'[\r\n]', ' ', onair)
                onair = re.sub(r'\s{2,}', ' ', onair)
                stlink = section.find('div', class_='stationlink')
                site = stlink.find('a', class_='site')
                if site:
                    site = site.get('href')
                else:
                    site = ''
                stream = stlink.find('a', class_='stm').get('href')
            except:
                print 'xxxxxxxxxxxxxxxx'
                print section.contents
                print 'xxxxxxxxxxxxxxxx'
                continue
            try:
                # parse asx
                if stream.startswith('mms://'):
                    pass
                else:
                    response = urllib.urlopen(stream)
                    data = response.read()
                    contenttype = response.info().gettype()
                    response.close()
                    if contenttype == 'video/x-ms-asf':
                        # 一部のデータでkodi.logにエラーが出力される
                        # 10:00:04 T:4568481792   ERROR: WARNING:root:Some characters could not be decoded, and were replaced with REPLACEMENT CHARACTER.
                        # 10:00:04 T:4568481792  NOTICE: .
                        # 文字コードが原因とおもわれるがurl抽出には影響ないので手当てしない
                        stream = BeautifulSoup(data).find('ref').get('href')
                    else:
                        print 'xxxxxxxxxxxxxxxx'
                        print id
                        print stream
                        print contenttype
                        print 'xxxxxxxxxxxxxxxx'
                        continue
            except:
                print 'xxxxxxxxxxxxxxxx'
                print id
                print stream
                print contenttype
                print 'xxxxxxxxxxxxxxxx'
                continue
            # pack as xml
            xmlstr = '<station>'
            xmlstr += '<id>simul_%s</id>' % (id)
            xmlstr += '<name>%s(%s)</name>' % (name,place)
            xmlstr += '<logo_large>%s%s</logo_large>' % (__service_url__,logo)
            xmlstr += '<url>%s</url>' % (stream)
            xmlstr += '<onair>%s</onair>' % (onair)
            xmlstr += '</station>'
            results.append(xmlstr)
            # pack as xml (for settings)
            xmlstr = '<setting label="%s(%s)" type="bool" id="simul_%s" default="false" enable="eq(%d,2)"/>' % (name,place,id,i)
            settings.append(xmlstr)
            i = i-1
        # write as xml
        f = codecs.open(__station_file2__,'w','utf-8')
        f.write('\n'.join(results))
        f.close()
        # write as xml (for settings)
        f = codecs.open(__settings_file__,'w','utf-8')
        f.write('\n'.join(settings))
        f.close()
        return '\n'.join(results)

    def getSettingsArray(self):
        f = codecs.open(__settings_file__,'r','utf-8')
        settings = f.read()
        f.close()
        return settings

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
