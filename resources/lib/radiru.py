# -*- coding: utf-8 -*-

import resources.lib.common as common
from common import(urlread,log,notify)

import os
import xml.dom.minidom
import codecs
import re
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
import exceptions
import json

__radiru_path__ = os.path.join(common.data_path, 'radiru')
if not os.path.isdir(__radiru_path__): os.makedirs(__radiru_path__)

__program_file__  = os.path.join(__radiru_path__, 'program.xml')
__station_file__  = os.path.join(__radiru_path__, 'station.xml')
__settings_file__ = os.path.join(__radiru_path__, 'settings.xml')

__station_url__   = 'http://www.nhk.or.jp/radio/config/config_web.xml'
__program_url__   = 'https://api.nhk.or.jp/r2/pg/now/4/%s/netradio.json'

__station_areajp__  = ['東京','札幌','仙台','名古屋','大阪','広島','松山','福岡']
__default_areajp__  = '東京'
__station_attr__  = [
    {
        'id':   'NHKR1',
        'name': 'NHKラジオ第1',
        'tag0': 'r1hls',
        'logo': 'https://www.nhk.or.jp/common/img/media/r1-200x200.png',
        'id1':   'n1',
    },
    {
        'id':   'NHKR2',
        'name': 'NHKラジオ第2',
        'tag0': 'r2hls',
        'logo': 'https://www.nhk.or.jp/common/img/media/r2-200x200.png',
        'id1':  'n2',
    },
    {
        'id':   'NHKFM',
        'name': 'NHK FM',
        'tag0': 'fmhls',
        'logo': 'https://www.nhk.or.jp/common/img/media/fm-200x200.png',
        'id1':  'n3',
    }
]

__lag__ = 40

#-------------------------------------------------------------------------------
class Radiru:

    def __init__(self, renew=False):
        self.id = 'radiru'
        try:
            area = common.addon.getSetting('area')
            self.areajp = __station_areajp__[int(area)]
        except:
            self.areajp = __default_areajp__
        # 放送局データと設定データを初期化
        self.getStationFile(renew)

    def getStationFile(self, renew=False):
        # キャッシュがあれば何もしない
        if renew == False and os.path.isfile(__station_file__) and os.path.isfile(__settings_file__):
            return
        # キャッシュがなければウェブから読み込む
        data = urlread(__station_url__)
        # データ変換
        dom = xml.dom.minidom.parseString(data)
        results = []
        settings = []
        i = -1
        data = dom.getElementsByTagName('data')
        for datum in data:
            areajp = datum.getElementsByTagName('areajp')[0].firstChild.data.strip().encode('utf-8')
            area = datum.getElementsByTagName('area')[0].firstChild.data.strip().encode('utf-8')
            areakey = datum.getElementsByTagName('areakey')[0].firstChild.data.strip().encode('utf-8')
            apikey = datum.getElementsByTagName('apikey')[0].firstChild.data.strip().encode('utf-8')
            if areajp == self.areajp:
                self.area = area
                self.areakey = areakey
                self.apikey = apikey
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
                    xmlstr = '    <setting label="%s" type="bool" id="radiru_%s" default="true" enable="eq(%d,2)"/>' % (name,id,i)
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
            data = urlread(__program_url__ % self.areakey)
        except:
            log('failed')
            return
        f = codecs.open(__program_file__,'w','utf-8')
        f.write(data.decode('utf-8'))
        f.close()

    def getProgramData(self, renew=False):
        if renew or not os.path.isfile(__program_file__):
            self.getProgramFile()
        jsonstr = open(__program_file__, 'r').read()
        #jsonstr = jsonstr.replace('\n', '<br/>')
        dom = json.loads(jsonstr)
        results = []
        for attr in __station_attr__:
            id1 = attr['id1']
            xmlstr = '<station id="radiru_%s">' % attr['id']
            # 放送中のプログラム
            for s in ('present','following'):
                try:
                    r = dom['nowonair_list'][id1][s]
                    # title
                    title = r['title']
                    # start & end
                    t = r['start_time']
                    ft = str(t[0:4])+str(t[5:7])+str(t[8:10])+str(t[11:13])+str(t[14:16])+str(t[17:19])
                    ftl = str(t[11:13])+str(t[14:16])
                    t = r['end_time']
                    to = str(t[0:4])+str(t[5:7])+str(t[8:10])+str(t[11:13])+str(t[14:16])+str(t[17:19])
                    tol = str(t[11:13])+str(t[14:16])
                    # xml
                    xmlstr += '<prog ft="%s" ftl="%s" to="%s" tol="%s">' % (ft,ftl,to,tol)
                    # title
                    xmlstr += '<title>%s</title>' % (title)
                    # description
                    for tag in ('subtitle','content','act','music','free'):
                        try:
                            text = r[tag]
                            text = re.sub(r'[\r\n\t]',' ',text)
                            text = re.sub(r'\s{2,}',' ',text)
                            text = re.sub(r'(^\s+|\s+$)','',text)
                            xmlstr += '<%s>%s</%s>' % (tag,text,tag)
                        except (exceptions.IndexError,exceptions.AttributeError):
                            continue
                    xmlstr += '</prog>'
                except exceptions.IndexError:
                    break
                except exceptions.KeyError:
                    continue
            xmlstr += '</station>'
            results.append(xmlstr)
        return '\n'.join(results)
