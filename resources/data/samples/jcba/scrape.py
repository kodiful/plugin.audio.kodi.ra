# -*- coding: utf-8 -*-

import os, sys
import urllib, urllib2
import re
import json

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
        buf3 = ['|地域|放送局|','|:---|:---|']
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
                    buf1.append({
                        'id': id,
                        'name': '%s(%s)' % (name.encode('utf-8'), place.encode('utf-8')),
                        'url': url,
                        'logo_large': logo,
                        'stream': stream,
                        'onair': onair.encode('utf-8')
                    })
                    buf2.append('    <setting label="{name}({place})" type="bool" id="{id}" default="false" enable="eq({i},2)"/>'.format(
                        id=id,
                        name=name.encode('utf-8'),
                        place=place.encode('utf-8'),
                        i=i
                    ))
                    buf3.append('|{place}|[{name}]({url})|'.format(
                        place=place.encode('utf-8'),
                        name=name.encode('utf-8'),
                        url=url
                    ))
                    i = i-1
        return buf1, buf2, buf3


if __name__  == '__main__':

    buf1, buf2, buf3 = Jcba().run()
    with open('station.json', 'w') as f:
        f.write(json.dumps(buf1, sort_keys=True, ensure_ascii=False, indent=4))
    with open('settings.xml', 'w') as f:
        f.write('\n'.join(buf2).replace('&','&amp;'))
    with open('wiki.md', 'w') as f:
        f.write('\n'.join(buf3).replace('&','&amp;'))
