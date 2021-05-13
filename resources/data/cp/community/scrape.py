# -*- coding: utf-8 -*-

# 「コミュニティ放送局一覧 - Wikipedia」 を元にネタを生成するスクリプト
# 注意: 
#  /resources/data/cp/jcba/scrape.pyを改造した物です。
#  サイトの構成(構造？)は，2021/05/01現在の物で動作を確認しています。

import os
import urllib
import json
import re

from bs4 import BeautifulSoup
from hashlib import md5

class Base:

    FBASE = 'station.json'    # base data (from Wiki)
    FLISR = 'station_lr.json' # ListenRadio data
    FJCBA = 'station_sj.json' # JCBA data
    FSR   = 'station_sr.json' # SimulRadio data
    
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
    def run(self, force = False):
        if not os.path.isfile(self.FILE) or force:
            data = self.load()
            self.write(data)
        data = self.read()
        return self.parse(data)


class wiki(Base):

    URL = 'https://ja.wikipedia.org/wiki/%E3%82%B3%E3%83%9F%E3%83%A5%E3%83%8B%E3%83%86%E3%82%A3%E6%94%BE%E9%80%81%E5%B1%80%E4%B8%80%E8%A6%A7' # コミュニティ放送局一覧 - Wikipedia
    FILE = 'wiki.xml'
    getforce = False # Wikiからネタ取得強制

    def chkMark1(self, mark):
        # int mark1
        # ● 	1	番組記号：JARTICによる交通情報を流す局
        # o 	2	番組記号：自社製作番組のみを放送している局
        # J 	4	番組記号：J-WAVEを再送信している局
        # M 	8	番組記号：ミュージックバードを再送信している局
        # S 	16	番組記号：スターデジオを再送信している局
        # e 	32	番組記号：上記以外の放送局などを再送信している局
        # k 	64	番組記号：番組を供給している放送局、もしくは全国同時ネットのキー局（注釈内は番組名）
        # UN	128	再送信記号：USENで再送信している局
        ret = 0
        if mark:
            if re.search('●', mark): ret = ret + 1
            if re.search('o', mark): ret = ret + 2
            if re.search('J', mark): ret = ret + 4
            if re.search('M', mark): ret = ret + 8
            if re.search('^S|・S$|・S・|^S$', mark): ret = ret + 16
            if re.search('e', mark): ret = ret + 32
            if re.search('k', mark): ret = ret + 64
            if re.search('UN', mark): ret = ret + 128
        return ret 

    def chkMark2(self, mark):
        # str mark2...とりあえず "Yes" を入れています。
        # SD	配信記号：放送局独自でサイマル配信を実施している局
        # SR	配信記号：SimulRadioでサイマル配信を実施している局
        # SJ	配信記号：JCBAインターネットサイマルラジオでサイマル配信を実施している局
        # SP	配信記号：FM++でサイマル配信を実施している局
        # FT	配信記号：FM聴でサイマル配信を実施している局
        # TR	配信記号：TuneIn Radioでサイマル配信を実施している局
        # LR	配信記号：ListenRadio（リスラジ）でサイマル配信を実施している局
        # US	配信記号：IBM Cloud Video（旧Ustream）でサイマル配信を実施している局
        # YL	配信記号：YouTube Liveでサイマル配信を実施している局
        ret = {
            'SD': '', 'SR': '', 'SJ': '', 'SP': '', 
            'FT': '', 'TR': '', 'LR': '', 'US': '', 
            'YL': ''
        }
        if mark:
            if re.search('SD', mark): ret['SD'] = 'Yes'
            if re.search('SR', mark): ret['SR'] = 'Yes'
            if re.search('SJ', mark): ret['SJ'] = 'Yes'
            if re.search('SP', mark): ret['SP'] = 'Yes'
            if re.search('FT', mark): ret['FT'] = 'Yes'
            if re.search('TR', mark): ret['TR'] = 'Yes'
            if re.search('LR', mark): ret['LR'] = 'Yes'
            if re.search('US', mark): ret['US'] = 'Yes'
            if re.search('YL', mark): ret['YL'] = 'Yes'
        return ret 

    def chkStatus(self, status):
        ret = 1
        if status:  
            if re.search('放送中', status): 
                ret = 0
            elif re.search('廃局', status): 
                ret = 1
            else: 
                ret = 2
        return ret

    def normalize(self, val):
        if val:
            val = re.sub(r'<.*?>', ' ', val)  # <>で括られた部分をhtmlタグとして削除
            val = re.sub(r'(?:　|\r\n|\n|\t)', ' ', val)  # 全角スペース、改行、タブを半角スペースに置換
            val = re.sub(r'\s{2,}', ' ', val)  # 二つ以上続く半角スペースは一つに置換
            val = re.sub(r'(^\s+|\s+$)', '', val)  # 先頭と末尾の半角スペースを削除
            val = re.sub(r'\[注\s\d+\]', '', val)  # 注釈(注)を削除
            val = re.sub(r'\[\d+\]', '', val)  # 注釈を削除
            
            # p[key] = val.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')
        return val

    # ファイルをパースする
    def parse(self, data):
        buf1 = []
        
        i = 0
        divs = BeautifulSoup(data, features='lxml').find_all('table', class_='wikitable sortable')
        for div in divs:
            rb = div.find_all('tr')
            for tr in rb:
                if tr.td == None: continue
                td = tr.find_all('td')

                name = self.normalize(tr.th.get_text())
                name = re.sub('\s☆$', '', name)  # ☆を削除
            
                stationname = self.normalize(td[0].get_text())
                callsign = td[1].get_text()
                areaid = int(callsign[4:5])
                frequency = self.normalize(re.sub('MHz', '', td[2].get_text()))
                address = self.normalize(td[3].get_text())
                output = self.normalize(re.sub('W', '', td[4].get_text()))
                repeator = re.sub('局', '', self.normalize(td[5].get_text()))
                repeator = 0 if repeator == 'なし' else repeator
                marks1 = self.chkMark1(self.normalize(td[6].get_text()))

                if len(td) == 8:
                    marks2 = self.chkMark2(self.normalize(td[6].get_text()))
                    status = td[7].get_text()
                elif len(td) == 9:
                    marks2 = self.chkMark2(self.normalize(td[7].get_text()))
                    status = td[8].get_text()
                else:
                    marks2 = ''
                    status = 2

                status = self.chkStatus(self.normalize(status))

                # wiki未更新2021/05/06
                # FM++移行済み?
                if name == 'エフエム西東京': marks2["SJ"] = ''; marks2["SP"] = 'Yes' 
                if name == 'iステーション': marks2["SJ"] = ''
                if name == 'Happy!FM': marks2["SJ"] = ''
                
                # 実はListenRadioが無い
                if name == "FM 愛'S": marks2["LR"] = '' 
                if name == 'FM HOT 839': marks2["LR"] = '' 
                if name == 'かつしかFM': marks2["LR"] = ''; marks2["YL"] = 'Yes'  # 20210501
                if name == 'FMやまと': marks2["LR"] = '' 
                if name == 'あづみ野エフエム': marks2["LR"] = ''
                if name == 'RADIO LOVEAT': marks2["LR"] = ''
                if name == 'Pitch FM': marks2["LR"] = ''
                if name == 'FM-HANAKO': marks2["LR"] = ''
                if name == 'エフエムわいわい': marks2["LR"] = ''
                if name == 'FM 丹波': marks2["LR"] = ''
                if name == 'FM TANABE': marks2["LR"] = ''
                if name == 'スターコーンFM': marks2["LR"] = ''
                if name == 'FMレキオ': marks2["LR"] = ''; marks2["SP"] = 'Yes' 
                if name == 'ちゅらハートエフエム本部': marks2["LR"] = ''; marks2["SP"] = 'Yes' 
                if name == 'FMくめじま': marks2["LR"] = ''

                # 実はSimulRadioが無い
                if name == "Honey FM": marks2["SR"] = '' 
                if name == "RADIOワンダーストレージFMドラマシティ": marks2["SR"] = '' # Orign
                if name == "エフエムしろいしWith-S": marks2["SR"] = '' # 都合により現在、配信を停止しております
                if name == "ラジオ3": marks2["SR"] = ''
                if name == "FMさくだいら": marks2["SR"] = ''; marks2["SP"] = 'Yes'
                if name == "Pitch FM": marks2["SR"] = ''; marks2["SP"] = 'Yes'
                if name == "サンシャインFM": marks2["SR"] = ''

                # if areaid == 1: print(i, areaid, name, stationname, callsign, frequency, address, output, repeator, marks1, marks2, status)
                buf1.append({
                    'areaid': areaid, # コールサインより抽出 北海道:1, 東北:2...四国:9, 九州・沖縄:0
                    'name': name,
                    'stationname': stationname,
                    'callsign': callsign,
                    'frequency': frequency,
                    'address': address,
                    'output': output,
                    'repeator': repeator,
                    'marks1': marks1,
                    'marks2': marks2,
                    'status': status
                })
                i = i + 1

        return buf1


class Jcba(Base):

    URL = 'http://www.jcbasimul.com'
    FILE = 'jcba.xml'

    # ファイルをパースする
    def parse(self, data):
        buf1 = []
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
                    id = jcbid.replace('JCB', 'jcba_')
                    stream = 'https://musicbird-hls.leanstream.co/musicbird/{id}.stream/playlist.m3u8'.format(id=jcbid)
                    onair = li.find('div', class_='text').find('p').string or ''
                    url = li.find('div', class_='officialLink').find('a').get('href')

                    cal = li.find('script') or ''
                    if cal:
                        cal = li.find('script').string
                        cal = re.search('\"(.+)\"', cal).group(0)[1:-1]
                        #print('match: %s' % x.group(0)[1:-1])
                        print('match: %s' % cal)

                    buf1.append({
                        'id': id,
                        'name': '%s(%s)' % (name, place),
                        'url': url,
                        'logo_large': logo,
                        'stream': stream,
                        'onair': onair,
                        'calendar': cal
                    })
                    i = i - 1
        return buf1


class Lisr(Base):

    URL = 'http://listenradio.jp/service/categorychannel.aspx?categoryid=10005' # サイマルのみ
    #URL = 'http://listenradio.jp/service/categorychannel.aspx?categoryid=99999' # 全ての局（リッスンラジオ公式や試験放送含む）
    FILE = 'categorychannel.json'

    # ファイルをパースする
    def parse(self, data):

        #cc = read(self.FILE) # categorychannel読み込み
        if data:
            cc = json.loads(data)
            channel = cc["Channel"]

            buf1 = [] # station.json
            i = -1

            for c in channel:
                name = c.get('ChannelName', 'n/a')
                name = re.sub('^\s|\s$', '', name)
                name = re.sub('（.*）', '', name) # "三角山放送局（札幌市西区）"対策
                place = re.split('にある|役所を|・|を中心とした|。',c.get('ChannelDetail', ''))[0]
                if re.match(r'fm那覇は',place): # "fm那覇"対策
                    place = place.split('fm那覇は')[1]
                logo = c.get('ChannelImage', '') # 正方形のアイコン，ChannelLogoは横長バナー
                id = 'lisr_' + str(c.get('ChannelId', ''))
                stream = c.get('ChannelHls', '')
                onair = c.get('ChannelDetail', '')
                url = '' # 生ネタに無し

                buf1.append({
                    'id': id,
                    'name': '%s(%s)' % (name, place),
                    'url': url,
                    'logo_large': logo,
                    'stream': stream,
                    'onair': onair
                })
                i = i - 1
            return buf1


class Simul(Base):

    URL = 'http://www.simulradio.info/'
    FILE = 'simulradio.xml'

    def loadasx(self, url):
        
        if re.search('simulradio', url): url = re.sub('^http:', 'https:', url)
        
        ret = url
        # <ref href="mms://hdv3.nkansai.tv/kiritampo"/>
        #res = urllib.request.urlopen(url, timeout=20.0)
        res = urllib.request.urlopen(url)
        data = res.read()
        res.close()
        data = data.decode('cp932') # Shift-JIS亜種?
        refs = BeautifulSoup(data, features='lxml').find_all('ref')
        if refs:
            for ref in refs:
                if not re.search('html$|mp3$', ref['href']):
                    ret = ref['href']
        else:
            #ret = url + " @" + BeautifulSoup(data, features='lxml').text
            ret = url + " @" + str(res.code)
        return ret

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
                ret = 'fmpp' # FM++
            elif 'media-gather' in url:
                ret = 'mg' # Flash Player時代の名残っぽい（FMひらかた 1局だけでlistenradioにも居る）
            else:
                ret = 'orig'
        return ret 

    def normalize(self, val):
        if val:
            val = re.sub(r'<.*?>', ' ', val)  # <>で括られた部分をhtmlタグとして削除
            val = re.sub(r'(?:　|\r\n|\n|\t)', ' ', val)  # 全角スペース、改行、タブを半角スペースに置換
            val = re.sub(r'\s{2,}', ' ', val)  # 二つ以上続く半角スペースは一つに置換
            val = re.sub(r'(^\s+|\s+$)', '', val)  # 先頭と末尾の半角スペースを削除
            # p[key] = val.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')
        return val

    # ファイルをパースする
    def parse(self, data):
        buf1 = []

        i = -1
        divs = BeautifulSoup(data, features='lxml').find_all('div', class_='radiobox')
        for div in divs:

            rb = div.find_all('tr')
            tr0 = rb[0].find_all('td')
            tr1 = rb[1].find_all('td')
            tr1p = tr1[0].find_all('p')

            cal = '' # カレンダーは，ありません
            logo = 'http://www.simulradio.info/{logo}'.format(logo = div.table.tr.img['src'])
            url =  tr1[0].a['href'] if tr1[0].a else ''
            name = self.normalize(tr1[0].a.text  if tr1[0].a else '')
            place = self.normalize(re.search('[\s\t].*$', tr1p[0].text).group() if re.search('[\s\t].*$', tr1p[0].text) else '')
            stream = tr0[1].a['href'] if tr0[1].a else ''
            streambase = ''
            onair = self.normalize(tr1p[1].text) if len(tr1p) == 2 else ''
            id = 'simu_' + md5(stream.encode()).hexdigest()

            if name == '': 
                if len(rb)==3: # case3対応(20210414 1局)
                    tr2 = rb[2].find_all('td')
                    tr2p = tr2[0].find_all('p')
                    url =  tr2p[0].a['href'] if tr2p[0].a else ''
                    name = self.normalize(tr2p[0].a.text  if tr2p[0].a else '')
                    place = self.normalize(re.search('[\s\t].*$', tr2p[0].text).group() if re.search('[\s\t].*$', tr2p[0].text) else '')
                    stream = tr1[0].a['href'] if tr1[0].a else ''
                    onair = 'irame'
                else: # case2対応(20210414 2局)
                    tr0p = tr0[0].find_all('p')
                    url =  tr0p[1].a['href'] if tr0p[1].a else ''
                    name = self.normalize(tr0p[1].a.text  if tr0p[1].a else '')
                    place = self.normalize(re.search('[\s\t].*$', tr0p[1].text).group() if re.search('[\s\t].*$', tr0p[1].text) else '')
                    stream = tr0[1].a['href'] if tr0[1].a else ''
                    onair = self.normalize(tr1p[0].text) if len(tr1p) == 1 else ''
                    id = 'simu_' + md5(stream.encode()).hexdigest()

            if place == '': # case4対応(閉局)
                place = self.normalize(re.search('[\s\t].*$', tr1p[1].text).group() if re.search('[\s\t].*$', tr1p[1].text) else '')
                #onair = self.normalize(tr1p[2].text) if len(tr1p) == 3 else ''
                onair = '閉局'

            streamsv = self.chkStreamUrl(stream if stream else '')

            if streamsv == 'simu' or ('orig' and re.search('asx$', stream)):
                streambase = stream
                stream = self.loadasx(stream)

            print(i, name, place, streamsv, stream)
            buf1.append({
                'id': id,
                'name': '%s(%s)' % (name, place),
                'url': url,
                'logo_large': logo,
                'stream': stream,
                'streambase': streambase,
                'onair': onair,
                'calendar': cal,
                'streamsv': streamsv
            })
            i = i - 1
        return buf1


class Marge(Base):

    FILE = ''

    def lisr(self):
        data = ''
        with open(self.FBASE, 'r') as f:
            data = f.read()
        base = json.loads(data)

        with open(self.FLISR, 'r') as f:
            data = f.read()
        lisr = json.loads(data)

        i = 0
        for l in lisr:
            na = re.sub('\(.*\)', '', l['name'])
            s = [b for b in base if 
                b['status'] == 0 and (
                        na == b['name']
                    or na == b['stationname']
                    or re.search(na, b['name'])
                    #or re.search(b['name'], na, re.IGNORECASE)
                    or na == re.sub(' ', '　', b['name'])
                    or na == re.sub('FM ', 'エフエム', b['name'])
                    or na == re.sub('FM', 'FM ', b['name'])
                    or na == re.sub('FM', 'エフエム', b['name'])
                    or na == re.sub('エフエム', 'FM', b['name'])
                    or na == re.sub('エフエム', 'FM', b['stationname'])
                    or na == re.sub('FM', 'ＦＭ', b['name'])
                    or re.sub('\s', '', na) == b['name']
                    or na == re.sub(' ', '', b['name'])
                    # 以下は個別対応
                    or (re.search('こしがやエフエム', na) and re.search('こしがやエフエム', b['name']))
                    or (re.search('RADIO3', na) and re.search('ラジオ3', b['name']))
                    or (re.search('77\.5LivelyFM', na) and re.search('ナナコライブリーエフエム', b['name']))
                    or (re.search('RadioCity', na) and re.search('RADIO CITY', b['name']))
                    or (re.search('FM N1', na) and re.search('えふえむ・エヌ・ワン', b['name']))
                    or (re.search('敦賀FM', na) and re.search('HARBOR STATION', b['name']))
                    or (re.search('MID FM', na) and re.search('MID-FM761', b['name']))
                    or (re.search('FM815', na) and re.search('FM81.5', b['name']))
                    or (re.search('CHOKUラジ！', na) and re.search('ちょっくらじお', b['name']))
                    or (re.search('FM87.0 RADIO MIX KYOTO', na) and re.search('Radio Mix Kyoto', b['name']))
                )
            ]
            if s:
                s[0]['marks2']['LR'] = l['id']
                if len(s) == 2: print(s)
            else:
                i = i + 1
                print("or (re.search('%s', na) and re.search('', b['name']))" % (na))

        #print(json.dumps(base, sort_keys=True, ensure_ascii=False, indent=2))
        with open(self.FBASE, 'w') as f:
            f.write(json.dumps(base, sort_keys=True, ensure_ascii=False, indent=2))

    def jcba(self):
        data = ''
        with open(self.FBASE, 'r') as f:
            data = f.read()
        base = json.loads(data)

        with open(self.FJCBA, 'r') as f:
            data = f.read()
        jcba = json.loads(data)

        i = 0
        for l in jcba:
            na = re.sub('\(.*\)', '', l['name']) # JCBA.name
            s = [b for b in base if 
                b['status'] == 0 and (
                    na == b['name']
                    or na == b['stationname']
                    or na == re.sub('FM', 'ＦＭ', b['name'])
                    or na == re.sub('エフエム', 'FM', b['name'])
                    or na == re.sub('エフエム', 'FM', b['stationname'])
                    or na == re.sub('エフエム', 'ＦＭ', b['name'])
                    or na == re.sub('FM', 'エフエム', b['name'])
                    or na == re.sub('ＦＭ', 'エフエム', b['name'])
                    or na == re.sub(' ', '　', b['name'])
                    or re.sub('\s', '', na) == b['name']
                    # 以下は個別対応
                    or (re.search('ＦＭごしょがわら', na) and re.search('FMごしょがわら G.Radio', b['name']))
                    or (re.search('FMONE', na) and re.search('FM One', b['name']))
                    or (re.search('H＠！FM', na) and re.search('H@!FM', b['name']))
                    or (re.search('エフエムNCV', na) and re.search('FM NCV おきたまGO!', b['name']))
                    or (re.search('えふえむい～じゃんおらんだらじお', na) and re.search('エフエムい〜じゃんおらんだラジオ', b['name']))
                    or (re.search('ハーバーラジオ', na) and re.search('ハーバーRADIO', b['name']))
                    or (re.search('ウルトラFM', na) and re.search('ULTRA FM', b['name']))
                    or (re.search('FMポコ', na) and re.search('FM POCO', b['name']))
                    or (re.search('エフエムきたかた', na) and re.search('喜多方シティエフエム', b['name']))
                    or (re.search('エフエム太郎', na) and re.search('FM TARO', b['name']))
                    or (re.search('ラジオ成田', na) and re.search('Radio NARITA', b['name']))
                    or (re.search('FMブルー湘南', na) and re.search('FM・ブルー湘南', b['name']))
                    or (re.search('鎌倉FM', na) and re.search('かまくらエフエム', b['name']))
                    or (re.search('ラジオチャット・ＦＭにいつ', na) and re.search('RADIO CHAT', b['name']))
                    or (re.search('FMうおぬま', na) and re.search('エフエム魚沼', b['name']))
                    or (re.search('LCV FM', na) and re.search('エルシーブイFM769', b['name']))
                    or (re.search('エフエムあづみの', na) and re.search('あづみ野エフエム', b['name']))
                    or (re.search('FMPiPi', na) and re.search('FM PiPi', b['name']))
                    or (re.search('FM Haro！', na) and re.search('FM Haro!', b['name']))
                    or (re.search('ボイスキュー', na) and re.search('ボイス・キュー', b['name']))
                    or (re.search('FM-Hi！', na) and re.search('FM-Hi!', b['name']))
                    or (re.search('COAST－FM76.7MHｚ', na) and re.search('COAST-FM', b['name']))
                    or (re.search('いなBee', na) and re.search('いなべエフエム', b['name']))
                    or (re.search('Suzuka Voice FM 78.3MHz', na) and re.search('鈴鹿ヴォイスFM', b['name']))
                    or (re.search('富山シティエフエム株式会社', na) and re.search('City-FM', b['name']))
                    or (re.search('FMまいづる', na) and re.search('エフエム舞鶴', b['name']))
                    or (re.search('ウメダFM Be Happy!789', na) and re.search('Be Happy! 789', b['name']))
                    or (re.search('エフエムみっきぃ', na) and re.search('エフエムみっきい', b['name']))
                    or (re.search('レディオ モモ', na) and re.search('Radio momo', b['name']))
                    or (re.search('FOR　LIFE　RADIO', na) and re.search('FOR LIFE RADIO FMみはら', b['name']))
                    or (re.search('COME ON ! FM', na) and re.search('COME ON! FM', b['name']))
                    or (re.search('Hello! NEW 新居浜 FM', na) and re.search('Hello!NEW 新居浜FM', b['name']))
                    or (re.search('DreamsFM', na) and re.search('ドリームスエフエム', b['name']))
                    or (re.search('Kappa　FM', na) and re.search('かっぱFM', b['name']))
                    or (re.search('NOASFM', na) and re.search('NOAS FM', b['name']))
                    or (re.search('FM-J エフエム上越', na) and re.search('FM-J', b['name']))
                    or (re.search('エフエムなぎさステーション', na) and re.search('なぎさステーション', b['name']))
                    or (re.search('RADIO SANQ', na) and re.search('Radio SANQ', b['name']))
                    or (re.search('i-wave', na) and re.search('i-wave 76.5 FM', b['name']))
                    or (re.search('FM-HANAKO 82.4MHz', na) and re.search('FM-HANAKO', b['name']))
                    or (re.search('タッキー816みのおエフエム', na) and re.search('タッキー816', b['name']))
                    or (re.search('エフエムいたみ', na) and re.search('ハッピーエフエムいたみ', b['name']))
                    or (re.search('FMビーチステーション', na) and re.search('ビーチステーション', b['name']))
                    or (re.search('エフエムおのみち', na) and re.search('エフエムおのみち79.4', b['name']))
                )
            ]
            if s:
                s[0]['marks2']['SJ'] = l['id']
                if len(s) == 2: print(s)
            else:
                i = i + 1
                print("or (re.search('%s', na) and re.search('', b['name']))" % (na))

        #print(json.dumps(base, sort_keys=True, ensure_ascii=False, indent=2))
        with open(self.FBASE, 'w') as f:
            f.write(json.dumps(base, sort_keys=True, ensure_ascii=False, indent=2))

    def sr(self):
        data = ''
        with open(self.FBASE, 'r') as f:
            data = f.read()
        base = json.loads(data)

        with open(self.FSR, 'r') as f:
            data = f.read()
        sr = json.loads(data)

        i = 0
        for l in sr:
            #if l["streamsv"] == "simu" and l["onair"] != "閉局":
            if l["onair"] != "閉局":
                na = re.sub('\(.*\)', '', l['name'])
                s = [b for b in base if b['status'] == 0 and (
                            na == b['name']
                        or na == b['stationname']
                        or re.search(na, b['name'])
                        #or re.search(b['name'], na, re.IGNORECASE)
                        or na == re.sub(' ', '　', b['name'])
                        or na == re.sub('FM ', 'エフエム', b['name'])
                        or na == re.sub('FM', 'FM ', b['name'])
                        or na == re.sub('FM', 'エフエム', b['name'])
                        or na == re.sub('エフエム', 'FM', b['name'])
                        or na == re.sub('エフエム', 'FM', b['stationname'])
                        or na == re.sub('FM', 'ＦＭ', b['name'])
                        or re.sub('\s', '', na) == b['name']
                        or na == re.sub(' ', '', b['name'])
                        # 以下は個別対応
                        or (re.search('FMわっぴ～', na) and re.search('エフエムわっぴー', b['name']))
                        or (re.search('e-niwaFM', na) and re.search('e-niwa', b['name']))
                        or (re.search('Wi-radio', na) and re.search('wi-radio', b['name']))
                        or (re.search('FMあばしり', na) and re.search('FM ABASHIRI', b['name']))
                        or (re.search('RADIO3', na) and re.search('ラジオ3', b['name']))
                        or (re.search('エフエム モットコム', na) and re.search('FM Mot.com', b['name']))
                        or (re.search('CLOVER MEDIA', na) and re.search('ナナコライブリーエフエム', b['name'])) # SRのネタオカシイ
                        or (re.search('FM kaon', na) and re.search('FMカオン', b['name']))
                        or (re.search('FM-UU', na) and re.search('FMうしくうれしく放送', b['name']))
                        or (re.search('FM-N1', na) and re.search('えふえむ・エヌ・ワン', b['name']))
                        or (re.search('ハーバーステーション', na) and re.search('HARBOR STATION', b['name']))
                        #or (re.search('エフエムわいわい', na) and re.search('エフエムわいわい', b['name']))
                        or (re.search('エフエムあまがさき', na) and re.search('FM aiai', b['name']))
                        or (re.search('RADIO MIX KYOTO', na) and re.search('Radio Mix Kyoto', b['name']))
                        or (re.search('FM高松', na) and re.search('FM81.5', b['name']))
                        or (re.search('あまみFM', na) and re.search('あまみエフエム ディ!ウェイヴ', b['name']))
                        or (re.search('エフエム ニライ', na) and re.search('FMニライ', b['name']))
                        or (re.search('FMもとぶ', na) and re.search('ちゅらハートエフエム本部', b['name']))

                    )
                ]
                if s:
                    s[0]['marks2']['SR'] = l['id']
                    #if l["streamsv"] == "csra": s[0]['marks2']['SR'] = 'csra'
                    #if l["streamsv"] == "simu": s[0]['marks2']['SR'] = l['id']
                    if l["streamsv"] == "lisr": s[0]['marks2']['SR'] = 'lisr'
                    #if l["streamsv"] == "knsi": s[0]['marks2']['SR'] = 'knsi'
                    if l["streamsv"] == "fmpp": s[0]['marks2']['SR'] = ''; s[0]['marks2']['SP'] = 'Yes'
                    #if l["streamsv"] == "orig": s[0]['marks2']['SR'] = 'orig'
                    #if len(s) == 2: print(s)
                else:
                    i = i + 1
                    print("or (re.search('%s', na) and re.search('', b['name']))" % (na))

        #print(json.dumps(base, sort_keys=True, ensure_ascii=False, indent=2))
        with open(self.FBASE, 'w') as f:
            f.write(json.dumps(base, sort_keys=True, ensure_ascii=False, indent=2))

    def mkSetting(self, i, n, buff):
        buff.append('      <setting label="{name}({place})" type="bool" id="{id}" default="false" enable="eq({i},2)"/>'.format(
            id = (
                n['marks2']['LR'] if n['marks2']['LR'] else
                n['marks2']['SJ'] if n['marks2']['SJ'] else
                n['marks2']['SR'] if n['marks2']['SR'] else
                '--'
            ),
            name = n['name'],
            place = n['address'],
            i = i
        ))
        """
        buff.append('      <setting label="{name}({place})" type="bool" id="{id}" default="false" visible="eq({i},{area})"/>'.format(
            id = (
                n['marks2']['LR'] if n['marks2']['LR'] else
                n['marks2']['SJ'] if n['marks2']['SJ'] else
                n['marks2']['SR'] if n['marks2']['SR'] else
                '--'
            ),
            name = n['name'],
            place = n['address'],
            i = i,
            area = n['areaid']
        ))        
        """
        return buff

    def listout(self):
        data = ''
        with open(self.FBASE, 'r') as f:
            data = f.read()
        base = json.loads(data)
        s = [b for b in base if 
                b['status'] == 0
            and ( 
                   b['marks2']['LR'] != ""
                or b['marks2']['SJ'] != ""
                or b['marks2']['SR'] != ""
            )
        ]
        s = sorted( s, key=lambda x: (x['areaid'], x['address']) )

        """
        for num in range(10):
            buf2 = [] # settingsN.xml
            i = 0
            for n in s:
                if n['areaid'] == num:
                    i = i - 1
                    self.mkSetting(i, n, buf2)
            with open('settings' + str(num) + '.xml', 'w') as f:
                f.write('\n'.join(buf2).replace('&', '&amp;'))
        """

        buf201 = [] # settingsN.xml
        i = 0
        for num in range(10):
            for n in s:
                if num == 1 and n['areaid'] == 1:
                    i = i - 1
                    self.mkSetting(i, n, buf201)
                if num == 2 and n['areaid'] == 2:
                    i = i - 1
                    self.mkSetting(i, n, buf201)
                if num == 3 and n['areaid'] == 3:
                    i = i - 1
                    self.mkSetting(i, n, buf201)
                if num in [4, 5] and n['areaid'] in [4, 5]:
                    i = i - 1
                    self.mkSetting(i, n, buf201)
                if num == 6 and n['areaid'] == 6:
                    i = i - 1
                    self.mkSetting(i, n, buf201)
                if num == 7 and n['areaid'] == 7:
                    i = i - 1
                    self.mkSetting(i, n, buf201)
                if num in [8, 9] and n['areaid'] in [8, 9]:
                    i = i - 1
                    self.mkSetting(i, n, buf201)
                if num == 0 and n['areaid'] == 0:
                    i = i - 1
                    self.mkSetting(i, n, buf201)

            with open('settings0' + str(num) + '.xml', 'w') as f:
                f.write('\n'.join(buf201).replace('&', '&amp;'))
            i = 0
            buf201 = []

        """
        buf22 = [] # settingsA.xml
        i = 0
        for n in s:
            i = i - 1
            self.mkSetting(i, n, buf22)
        with open('settingsA.xml', 'w') as f:
            f.write('\n'.join(buf22).replace('&', '&amp;'))
        """

        buf3 = ['# 局リスト', '|No|地域Cd|所在地|放送局|選択Stream|', '|--:|:--:|:---|:---|:---|'] # wiki.md
        i = 0
        for n in s:
            i = i + 1
            buf3.append('|{no}|{id}|{place}|{name}|{select}|'.format(
                no = i,
                id = n['areaid'],
                place = n['address'],
                name =  n['name'],
                select = (
                    n['marks2']['LR'] if n['marks2']['LR'] else
                    n['marks2']['SJ'] if n['marks2']['SJ'] else
                    n['marks2']['SR'] if n['marks2']['SR'] else
                    '--'
                )
            ))
            print(i, n['areaid'], n['name'], n['marks2']['LR'] if n['marks2']['LR'] else n['marks2']['SJ'] if n['marks2']['SJ'] else n['marks2']['SR'] if n['marks2']['SR'] else '--')

        return buf2, buf3

    def marge(self):
        self.lisr()
        self.jcba()
        self.sr()
        return self.listout()


if __name__ == '__main__':

    flg = False # "True" で，Webからネタ取得を強制

    buf1 = wiki().run(flg)
    with open(Base.FBASE, 'w') as f:
        f.write(json.dumps(buf1, sort_keys=True, ensure_ascii=False, indent=2))

    buf1 = Jcba().run(flg)
    with open(Base.FJCBA, 'w') as f:
        f.write(json.dumps(buf1, sort_keys=True, ensure_ascii=False, indent=2))

    buf1 = Lisr().run(flg)
    with open(Base.FLISR, 'w') as f:
        f.write(json.dumps(buf1, sort_keys=True, ensure_ascii=False, indent=2))

    buf1 = Simul().run(flg)
    with open(Base.FSR, 'w') as f:
        f.write(json.dumps(buf1, sort_keys=True, ensure_ascii=False, indent=2))

    buf2, buf3 = Marge().marge()
    with open('StationList.md', 'w') as f:
        f.write('\n'.join(buf3).replace('&', '&amp;'))
