# -*- coding: utf-8 -*-

import os
import urllib, urllib2
import xml.dom.minidom
import codecs

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
__biglogo_url__   = 'http://www3.nhk.or.jp/netradio/files/img/biglogo.gif'
#__biglogo_url__  = 'http://www.nhk.or.jp/radiru/common/images/footer_logo01.gif'
#__biglogo_url__  = 'http://www.nhk.or.jp/radiru/common/images/footer_logo02.gif'
#__biglogo_url__  = 'http://www.nhk.or.jp/radiru/common/images/footer_logo03.gif'

#-------------------------------------------------------------------------------
class Radiru:

    def __init__(self):
        self.id = 'radiru'
        try:
            area = __settings__.getSetting('area')
            self.area = ['東京','仙台','名古屋','大阪'][int(area)]
        except:
            self.area = '東京'
        #self.protocol = 'rtmp'
        self.protocol = 'wms'
    
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

    def getStationArray(self):
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
        stations = [['NHKR1','NHKラジオ第1','r1','r1_wms'],['NHKR2','NHKラジオ第2','r2','r2_wms'],['NHKFM','NHK FM','fm','fm_wms']]
        i = -1
        data = dom.getElementsByTagName('data')
        for datum in data:
            area = datum.getElementsByTagName('areajp')[0].firstChild.data.strip().encode('utf-8')
            if area == self.area:
                for station in stations:
                    # pack as xml
                    id = station[0].decode('utf-8')
                    name = station[1].decode('utf-8')
                    if self.protocol == 'rtmp':
                        url = datum.getElementsByTagName(station[2])[0].firstChild.data.strip()
                        url = '%s swfUrl=%s swfVfy=1 live=1' % (url,__player_url__)
                    elif self.protocol == 'wms':
                        url = datum.getElementsByTagName(station[3])[0].firstChild.data.strip()
                        response = urllib.urlopen(url)
                        data = response.read()
                        response.close()
                        url = xml.dom.minidom.parseString(data).getElementsByTagName('REF')[0].getAttribute('HREF')
                    # pack as xml
                    xmlstr = '<station>'
                    xmlstr += '<id>radiru_%s</id>' % (id)
                    xmlstr += '<name>%s</name>' % (name)
                    xmlstr += '<logo_large>%s</logo_large>' % (__biglogo_url__)
                    xmlstr += '<url>%s</url>' % (url)
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
    
    def getSettingsArray(self):
        f = codecs.open(__settings_file__,'r','utf-8')
        settings = f.read()
        f.close()
        return settings
    
    def getProgramFile(self):
        response = urllib.urlopen(__program_url__)
        data = response.read()
        response.close()
        f = codecs.open(__program_file__,'w','utf-8')
        f.write(data.decode('utf-8'))
        f.close()

    def getProgramArray(self):
        xmlstr = open(__program_file__, 'r').read()
        dom = xml.dom.minidom.parseString(xmlstr)
        results = []
        stations = [['NHKR1','netr10','netr1F1'],['NHKR2','netr20','netr2F1'],['NHKFM','netfm0','netfmF1']]
        for station in stations:
            xmlstr = '<station id="radiru_%s">' % station[0]
            # 放送中のプログラム
            r10 = dom.getElementsByTagName(station[1])
            if r10.length:
                t = r10[0].getElementsByTagName('starttime')[0].firstChild.data.strip()
                ft = str(t[0:4])+str(t[5:7])+str(t[8:10])+str(t[11:13])+str(t[14:16])+str(t[17:19])
                ftl = str(t[11:13])+str(t[14:16])
                t = r10[0].getElementsByTagName('endtime')[0].firstChild.data.strip()
                to = str(t[0:4])+str(t[5:7])+str(t[8:10])+str(t[11:13])+str(t[14:16])+str(t[17:19])
                tol = str(t[11:13])+str(t[14:16])
                xmlstr += '<prog ft="'+ft+'" ftl="'+ftl+'" to="'+to+'" tol="'+tol+'">'
                xmlstr += '<title>'+r10[0].getElementsByTagName('title')[0].firstChild.data.strip()+'</title>'
                try:
                    content = r10[0].getElementsByTagName('free')[0].firstChild.data.strip()
                    content = re.sub(r'[\r\n]', ' ', content)
                    content = re.sub(r'\s{2,}', ' ', content)
                    xmlstr += '<desc>'+content+'</desc>'
                except:
                    try:
                        content = r10[0].getElementsByTagName('content')[0].firstChild.data.strip()
                        content = re.sub(r'[\r\n]', ' ', content)
                        content = re.sub(r'\s{2,}', ' ', content)
                        xmlstr += '<desc>'+content+'</desc>'
                    except:
                        pass
                xmlstr += '</prog>'
                # 次のプログラム
                r11 = dom.getElementsByTagName(station[2])
                if r11.length:
                    t = r11[0].getElementsByTagName('starttime')[0].firstChild.data.strip()
                    ft = str(t[0:4])+str(t[5:7])+str(t[8:10])+str(t[11:13])+str(t[14:16])+str(t[17:19])
                    ftl = str(t[11:13])+str(t[14:16])
                    t = r11[0].getElementsByTagName('endtime')[0].firstChild.data.strip()
                    to = str(t[0:4])+str(t[5:7])+str(t[8:10])+str(t[11:13])+str(t[14:16])+str(t[17:19])
                    tol = str(t[11:13])+str(t[14:16])
                    xmlstr += '<prog ft="'+ft+'" ftl="'+ftl+'" to="'+to+'" tol="'+tol+'">'
                    xmlstr += '<title>'+r11[0].getElementsByTagName('title')[0].firstChild.data.strip()+'</title>'
                    try:
                        content = r11[0].getElementsByTagName('free')[0].firstChild.data.strip()
                        content = re.sub(r'[\r\n]', ' ', content)
                        content = re.sub(r'\s{2,}', ' ', content)
                        xmlstr += '<desc>'+content+'</desc>'
                    except:
                        try:
                            content = r11[0].getElementsByTagName('content')[0].firstChild.data.strip()
                            content = re.sub(r'[\r\n]', ' ', content)
                            content = re.sub(r'\s{2,}', ' ', content)
                            xmlstr += '<desc>'+content+'</desc>'
                        except:
                            pass
                    xmlstr += '</prog>'
            xmlstr += '</station>'
            results.append(xmlstr)
        return '\n'.join(results)
