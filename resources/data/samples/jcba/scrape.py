# -*- coding: utf-8 -*-

import os, sys
import urllib, urllib2
import re

from bs4 import BeautifulSoup


class Base:

    URL  = ''
    FILE = ''

    # ページを読み込む
    def load(self):
        res = urllib.urlopen(self.URL)
        data = res.read()
        res.close()
        return data

    # ファイルを書き込む
    def write(self, data):
        with open(self.FILE, 'w') as f:
            f.write(data)

    # ファイルを読み込む
    def read(self):
        with open(self.FILE, 'r') as f:
            data = f.read()
        return data

    # ファイルをパースする
    def parse(self, data):
        return []

    # 一連の処理を実行する
    def run(self):
        if not os.path.isfile(self.FILE):
            data = self.load()
            self.write(data)
        data = self.read()
        return self.parse(data)


class Jcba(Base):

    URL  = 'http://www.jcbasimul.com'
    FILE = 'jcba.xml'

    # ファイルをパースする
    def parse(self, data):
        buf1 = []
        buf2 = []
        buf3 = [u'|地域|放送局|',u'|:---|:---|']
        i = -1
        divs = BeautifulSoup(data, features='lxml').find_all('div', class_='areaList')
        for div in divs:
            uls = div.find_all('ul', class_='cf')
            for ul in uls:
                lis = ul.find_all('li')
                for li in lis:
                    name, place = li.find('h3').string.split(' / ')
                    logo = li.find('div', class_='bnr').find('img').get('src')
                    jcbid = li.find('div', class_='rplayer').get('id')
                    id = jcbid.replace('JCB','jcba_')
                    stream = 'https://musicbird-hls.leanstream.co/musicbird/{id}.stream/playlist.m3u8'.format(id=jcbid)
                    onair = li.find('div', class_='text').find('p').string or ''
                    url = li.find('div', class_='officialLink').find('a').get('href')
                    buf1.append(u'<station><id>{id}</id><name>{name}({place})</name><url>{url}</url><logo_large>{logo}</logo_large><stream>{stream}</stream><opt></opt><onair>{onair}</onair></station>'.format(
                        id=id,
                        name=name,
                        place=place,
                        url=url,
                        logo=logo,
                        stream=stream,
                        onair=onair
                    ))
                    buf2.append(u'    <setting label="{name}({place})" type="bool" id="{id}" default="false" enable="eq({i},2)"/>'.format(
                        id=id,
                        name=name,
                        place=place,
                        i=i
                    ))
                    buf3.append(u'|{place}|[{name}]({url})|'.format(
                        place=place,
                        name=name,
                        url=url
                    ))
                    i = i-1
        return buf1, buf2, buf3


if __name__  == '__main__':

    buf1, buf2, buf3 = Jcba().run()
    with open('station.xml', 'w') as f:
        f.write('\n'.join(buf1).replace('&','&amp;').encode('utf-8'))
    with open('settings.xml', 'w') as f:
        f.write('\n'.join(buf2).replace('&','&amp;').encode('utf-8'))
    with open('wiki.md', 'w') as f:
        f.write('\n'.join(buf3).replace('&','&amp;').encode('utf-8'))
