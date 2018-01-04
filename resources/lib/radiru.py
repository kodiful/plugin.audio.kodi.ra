# -*- coding: utf-8 -*-

import resources.lib.common as common
from common import(log,notify)

import os
import urllib, urllib2
import xml.dom.minidom
import codecs
import re
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
import exceptions

__radiru_path__ = os.path.join(common.data_path, 'radiru')
if not os.path.isdir(__radiru_path__): os.makedirs(__radiru_path__)

__program_file__  = os.path.join(__radiru_path__, 'program.xml')
__station_file__  = os.path.join(__radiru_path__, 'station.xml')
__settings_file__ = os.path.join(__radiru_path__, 'settings.xml')

__station_url__   = 'http://www.nhk.or.jp/radio/config/config_web.xml'
__program_url__   = 'http://www2.nhk.or.jp/hensei/api/noa.cgi'

__station_area__  = ['東京','札幌','仙台','名古屋','大阪','広島','松山','福岡']
__default_area__  = '東京'
__station_attr__  = [
    {
        'id':   'NHKR1',
        'name': 'NHKラジオ第1',
        'tag0': 'r1hls',
        'logo': 'http://www.nhk.or.jp/r2/images/symbol_r1.png',
        'tag1': 'netr10',
        'tag2': 'netr1F1'
    },
    {
        'id':   'NHKR2',
        'name': 'NHKラジオ第2',
        'tag0': 'r2hls',
        'logo': 'http://www.nhk.or.jp/r2/images/symbol_r2.png',
        'tag1': 'netr20',
        'tag2': 'netr2F1'
    },
    {
        'id':   'NHKFM',
        'name': 'NHK FM',
        'tag0': 'fmhls',
        'logo': 'http://www.nhk.or.jp/r2/images/symbol_fm.png',
        'tag1': 'netfm0',
        'tag2': 'netfmF1'
    }
]

__lag__ = 40

#-------------------------------------------------------------------------------
class Radiru:

    def __init__(self, renew=False):
        self.id = 'radiru'
        try:
            area = common.addon.getSetting('area')
            self.area = __station_area__[int(area)]
        except:
            self.area = __default_area__
        # 放送局データと設定データを初期化
        self.getStationFile(renew)

    def getStationFile(self, renew=False):
        # キャッシュがあれば何もしない
        if renew == False and os.path.isfile(__station_file__) and os.path.isfile(__settings_file__):
            return
        # キャッシュがなければウェブから読み込む
        response = urllib.urlopen(__station_url__)
        data = response.read()
        response.close()
        # データ変換
        dom = xml.dom.minidom.parseString(data)
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
                    url = datum.getElementsByTagName(attr['tag0'])[0].firstChild.data.strip()
                    # pack as xml
                    xmlstr = '<station>'
                    xmlstr += '<id>radiru_%s</id>' % (id)
                    xmlstr += '<name>%s</name>' % (name)
                    xmlstr += '<logo_large>%s</logo_large>' % (logo)
                    xmlstr += '<url>%s</url>' % (url)
                    xmlstr += '<lag>%d</lag>' % (__lag__)
                    xmlstr += '</station>'
                    results.append(xmlstr)
                    # pack as xml (for settings)
                    xmlstr = '    <setting label="%s" type="bool" id="radiru_%s" default="false" enable="eq(%d,2)"/>' % (name,id,i)
                    settings.append(xmlstr)
                    i = i-1
                break
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
        stations = f.read()
        f.close()
        return stations

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
            log('failed')
            return
        f = codecs.open(__program_file__,'w','utf-8')
        f.write(data.decode('utf-8'))
        f.close()

    def getProgramData(self, renew=False):
        if renew or not os.path.isfile(__program_file__):
            self.getProgramFile()
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
