# -*- coding: utf-8 -*-

# csra.fmのWebサイトからネタを生成するスクリプト
# 注意: 
#  /resources/data/cp/jcba/scrape.pyを改造した物です。
#  サイトの構成(情報)は，2021/04/14現在のものを使用しています。

import os
import urllib
import json
import re

from bs4 import BeautifulSoup
from hashlib import md5

class Base:

    URL = ''
    FILE = ''

    # ページを読み込む
    def load(self):
        res = urllib.request.urlopen(self.URL)
        data = res.read()
        res.close()
        return data

    # ファイルを書き込む
    def write(self, data):
        #with open(self.FILE, 'w') as f: # errorする…
        with open(self.FILE, 'wb') as f:
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

    URL = 'http://csra.fm/stationlist/'
    FILE = 'csra.xml'

    def chkStreamUrl(self, url):
        ret = ''
        if url:
            if 'listenradio' in url:
                ret = 'lisr'
            elif 'csra' in url:
                ret = 'csra' # *.asx
            elif 'simulradio' in url:
                ret = 'simu' # *.asx
            elif 'nkansai' in url:
                ret = 'knsi' # *.asxなしで，nkansai直
            elif 'fmplapla' in url:
                ret = 'fmpp'
            elif 'media-gather' in url:
                ret = 'mg' # Flash Player時代の名残っぽい（FMひらかた 1局だけでlistenradioにも居る）
            else:
                ret = 'orig'
        return ret 

    # ファイルをパースする
    def parse(self, data):
        buf1 = []
        buf2 = []
        buf22 = []
        buf3 = ['|地域|放送局|', '|:---|:---|']
        i = -1
        divs = BeautifulSoup(data, features='lxml').find_all('section')
        for div in divs:
            # print(i, div.find('h1'))            
            cal = '' # カレンダーは，ありません
            name = div.find('h1').string if div.find('h1') else ''
            place = div.find('p').string if div.find('p') else ''
            if div.find('div', class_='stationlogo'):
                if div.find('div', class_='stationlogo').find('img'):
                    logo = 'http://csra.fm{logo}'.format(logo = div.find('div', class_='stationlogo').find('img').get('src'))
            if div.find('div', class_='stationlink'):
                if div.find('div', class_='stationlink').find('a', class_='stm'):
                    stream = div.find('div', class_='stationlink').find('a', class_='stm').get('href') # class="stm2"は無視してます。
                if div.find('div', class_='stationlink').find('a', class_='site'):
                    url =  div.find('div', class_='stationlink').find('a', class_='site').get('href')
            if div.find('a', class_='stationlist'):
                onair = div.find('a', class_='stationlist').get('title') # 適当な物が，ありません
            id = 'csra_' + md5(url.encode()).hexdigest()
            streamsv = self.chkStreamUrl(stream)

            buf1.append({
                'id': id,
                'name': '%s(%s)' % (name, place),
                'url': url,
                'logo_large': logo,
                'stream': stream,
                'onair': onair,
                'calendar': cal,
                'streamsv': streamsv
            })
            if i>=-75:
                buf2.append('    <setting label="{name}({place})" type="bool" id="{id}" default="false" enable="eq({i},2)"/>'.format(
                    id=id,
                    name=name,
                    place=place,
                    i=i
                ))
            else:
                buf22.append('    <setting label="{name}({place})" type="bool" id="{id}" default="false" enable="eq({i},2)"/>'.format(
                    id=id,
                    name=name,
                    place=place,
                    i=i+75
                ))
            buf3.append('|{place}|[{name}]({url})|'.format(
                place=place,
                name=name,
                url=url
            ))
            i = i - 1
        return buf1, buf2, buf22, buf3


if __name__ == '__main__':

    buf1, buf2, buf22, buf3 = Jcba().run()
    with open('station.json', 'w') as f:
        f.write(json.dumps(buf1, sort_keys=True, ensure_ascii=False, indent=4))
    with open('settings.xml', 'w') as f:
        f.write('\n'.join(buf2).replace('&', '&amp;'))
    with open('settings2.xml', 'w') as f:
        f.write('\n'.join(buf22).replace('&', '&amp;'))
    with open('wiki.md', 'w') as f:
        f.write('\n'.join(buf3).replace('&', '&amp;'))
