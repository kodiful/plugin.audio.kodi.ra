# -*- coding: utf-8 -*-

import os
import urllib, urllib2
import xml.dom.minidom
import codecs
import re
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
import exceptions

from common import(log)
from common import(__data_path__)
from common import(__settings__)

__radiru_path__ = os.path.join(__data_path__, 'radiru')
if not os.path.isdir(__radiru_path__): os.makedirs(__radiru_path__)

__program_file__  = os.path.join(__radiru_path__, 'program.xml')
__station_file__  = os.path.join(__radiru_path__, 'station.xml')
__station_file2__ = os.path.join(__radiru_path__, 'station2.xml')
__settings_file__ = os.path.join(__radiru_path__, 'settings.xml')

#__player_url__   = 'http://www3.nhk.or.jp/netradio/files/swf/rtmpe.swf'
__player_url__    = 'http://www3.nhk.or.jp/netradio/files/swf/rtmpe201406.swf?ver.2'
__station_url__   = 'http://www3.nhk.or.jp/netradio/app/config_pc.xml'
__program_url__   = 'http://www2.nhk.or.jp/hensei/api/noa.cgi'

__station_area__  = ['東京','仙台','名古屋','大阪']
__default_area__  = '東京'
__station_attr__  = [
    {
        'id':   'NHKR1',
        'name': 'NHKラジオ第1',
        'tag0': 'r1',
        'logo': 'http://www.nhk.or.jp/r2/images/symbol_r1.png',
        'tag1': 'netr10',
        'tag2': 'netr1F1'
    },
    {
        'id':   'NHKR2',
        'name': 'NHKラジオ第2',
        'tag0': 'r2',
        'logo': 'http://www.nhk.or.jp/r2/images/symbol_r2.png',
        'tag1': 'netr20',
        'tag2': 'netr2F1'
    },
    {
        'id':   'NHKFM',
        'name': 'NHK FM',
        'tag0': 'fm',
        'logo': 'http://www.nhk.or.jp/r2/images/symbol_fm.png',
        'tag1': 'netfm0',
        'tag2': 'netfmF1'
    }
]

#-------------------------------------------------------------------------------
class Radiru:

    def __init__(self):
        self.id = 'radiru'
        try:
            area = __settings__.getSetting('area')
            self.area = __station_area__[int(area)]
        except:
            self.area = __default_area__

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
        f.write(data.decode('utf-8'))
        f.close()

    def getStationData(self):
        # キャッシュがある場合
        if os.path.isfile(__station_file2__):
            f = codecs.open(__station_file2__,'r','utf-8')
            data = f.read()
            f.close()
            return data
        # キャッシュがない場合
        xmlstr = open(__station_file__, 'r').read()
        dom = xml.dom.minidom.parseString(xmlstr)
        results = []
        settings = []
        i = -1
        data = dom.getElementsByTagName('data')
        for datum in data:
            area = datum.getElementsByTagName('areajp')[0].firstChild.data.strip().encode('utf-8')
            if area == self.area:
                for attr in __station_attr__:
                    # pack as xml
                    id = attr['id'].decode('utf-8')
                    name = attr['name'].decode('utf-8')
                    logo = attr['logo'].decode('utf-8')
                    url1 = datum.getElementsByTagName(attr['tag0'])[0].firstChild.data.strip()
                    url = '%s swfUrl=%s swfVfy=1 live=1' % (url1,__player_url__)
                    options = '-r "%s" -W "%s" -v' % (url1,__player_url__)
                    # pack as xml
                    xmlstr = '<station>'
                    xmlstr += '<id>radiru_%s</id>' % (id)
                    xmlstr += '<name>%s</name>' % (name)
                    xmlstr += '<logo_large>%s</logo_large>' % (logo)
                    xmlstr += '<url>%s</url>' % (url)
                    xmlstr += '<options>%s</options>' % (options)
                    xmlstr += '</station>'
                    results.append(xmlstr)
                    # pack as xml (for settings)
                    xmlstr = '<setting label="%s" type="bool" id="radiru_%s" default="false" enable="eq(%d,2)"/>' % (name,id,i)
                    settings.append(xmlstr)
                    i = i-1
                break
        # write as xml
        f = codecs.open(__station_file2__,'w','utf-8')
        f.write('\n'.join(results))
        f.close()
        # write as xml (for settings)
        f = codecs.open(__settings_file__,'w','utf-8')
        f.write('\n'.join(settings))
        f.close()
        return '\n'.join(results)

    def getSettingsData(self):
        f = codecs.open(__settings_file__,'r','utf-8')
        settings = f.read()
        f.close()
        return settings

    def getProgramFile(self):
        try:
            response = urllib.urlopen(__program_url__)
            data = response.read()
            response.close()
        except:
            log('failed in radiru')
            return
        f = codecs.open(__program_file__,'w','utf-8')
        f.write(data.decode('utf-8'))
        f.close()

    def getProgramData(self):
        xmlstr = open(__program_file__, 'r').read()
        dom = xml.dom.minidom.parseString(xmlstr)
        results = []
        for attr in __station_attr__:
            xmlstr = '<station id="radiru_%s">' % attr['id']
            # 放送中のプログラム
            for s in [attr['tag1'],attr['tag2']]:
                try:
                    r = dom.getElementsByTagName(s)[0]
                    # title
                    title = r.getElementsByTagName('title')[0].firstChild.data.strip()
                    # start & end
                    t = r.getElementsByTagName('starttime')[0].firstChild.data.strip()
                    ft = str(t[0:4])+str(t[5:7])+str(t[8:10])+str(t[11:13])+str(t[14:16])+str(t[17:19])
                    ftl = str(t[11:13])+str(t[14:16])
                    t = r.getElementsByTagName('endtime')[0].firstChild.data.strip()
                    to = str(t[0:4])+str(t[5:7])+str(t[8:10])+str(t[11:13])+str(t[14:16])+str(t[17:19])
                    tol = str(t[11:13])+str(t[14:16])
                    # xml
                    xmlstr += '<prog ft="%s" ftl="%s" to="%s" tol="%s">' % (ft,ftl,to,tol)
                    # title
                    xmlstr += '<title>%s</title>' % (title)
                    # description
                    for tag in ['subtitle','content','act','music','free']:
                        try:
                            text = r.getElementsByTagName(tag)[0].firstChild.data.strip()
                            text = re.sub(r'[\r\n\t]',' ',text)
                            text = re.sub(r'\s{2,}',' ',text)
                            text = re.sub(r'(^\s+|\s+$)','',text)
                            #text = text.replace('&lt;','<').replace('&gt;','>').replace('&quot;','"').replace('&amp;','&')
                            #text = text.replace('&','&amp;').replace('"','&quot;').replace('>','&gt;').replace('<','&lt;')
                            xmlstr += '<%s>%s</%s>' % (tag,text,tag)
                        except (exceptions.IndexError,exceptions.AttributeError):
                            continue
                    xmlstr += '</prog>'
                except exceptions.IndexError:
                    break
            xmlstr += '</station>'
            results.append(xmlstr)
        return '\n'.join(results)
