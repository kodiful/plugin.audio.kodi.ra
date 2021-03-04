# -*- coding: utf-8 -*-

from resources.lib.const import Const
from resources.lib.common import log
from resources.lib.common import read_file
from resources.lib.common import read_json
from resources.lib.common import strptime
from resources.lib.holiday import Holiday

import os
import sys
import glob
import shutil
import re

import xbmcgui
import xbmcplugin

from hashlib import md5
from xml.sax.saxutils import escape, unescape


class Contents:

    def __init__(self, key=''):
        # for backward compatibility
        rss = Const.GET('rss')
        if rss == 'true' or rss == 'false':
            pass
        elif rss == '0':
            Const.SET('rss', 'false')
        else:
            Const.SET('rss', 'true')
            Const.SET('rss_num', rss)
        # 指定されたキー
        self.key = key
        # RSS関連のパラメータ
        if Const.GET('rss') == 'true' and re.search(r'^https?://', Const.GET('rss_url')):
            # RSSのルートパスを補正
            url = Const.GET('rss_url')
            if not url.endswith('/'):
                url = '%s/' % url
                Const.SET('rss_url', url)
            # RSSのルートパス
            self.rssroot = os.path.dirname(url)
            # キー文字列のハッシュ
            self.hexdigest = md5(key.encode()).hexdigest() if key else ''
            # RSSのファイル名
            self.filename = 'rss_%s.xml' % self.hexdigest if key else 'rss.xml'
            # RSSのURL
            self.url = '%s/%s' % (self.rssroot, self.filename) if self.rssroot else ''
        else:
            self.rssroot = ''
            self.hexdigest = ''
            self.filename = ''
            self.url = ''

    def contents(self):
        # jsonファイルとmp3ファイルの両方があるものを抽出
        contents = []
        for file in glob.glob(os.path.join(Const.DOWNLOAD_PATH, '*.json')):
            json_file = file
            mp3_file = file.replace('.json', '.mp3')
            if os.path.isfile(mp3_file):
                contents.append(read_json(json_file))
            else:
                log('file lost (or in downloading):{file}'.format(file=mp3_file))
        # keyが指定されていたらフィルタ
        if self.key:
            contents = list(filter(lambda p: p['key'] == self.key, contents))
        # 開始時刻の逆順でソート
        return sorted(contents, key=lambda p: p['ft'], reverse=True)

    def show(self):
        # 日付フォーマット
        h = Holiday()
        # 時間の逆順にソートして表示
        for p in self.contents():
            # title
            title = '%s [COLOR khaki]%s[/COLOR] [COLOR khaki](%s)[/COLOR]' % (h.format(p['ft']), p['title'], p['name'])
            # logo
            id = p['gtvid'].split('_')
            logopath = os.path.join(Const.MEDIA_PATH, 'logo_%s_%s.png' % (id[0], id[1]))
            if not os.path.isfile(logopath):
                logopath = 'DefaultFile.png'
            # listitemを追加
            li = xbmcgui.ListItem(title)
            li.setArt({'icon': logopath, 'thumb': logopath})
            comment = p['description']
            comment = re.sub(r'&lt;.*?&gt;', '\n', comment)
            comment = re.sub(r'\n{2,}', '\n', comment)
            comment = re.sub(r'^\n+', '', comment)
            comment = re.sub(r'\n+$', '', comment)
            li.setInfo(type='music', infoLabels={'title': p['title'], 'duration': p['duration'], 'artist': p['name'], 'comment': comment})
            li.setProperty('IsPlayable', 'true')
            # context menu
            li.addContextMenuItems([(Const.STR(30314), 'RunPlugin(%s?action=deleteDownload&id=%s)' % (sys.argv[0], p['gtvid']))], replaceItems=True)
            # add directory item
            # file
            mp3_file = os.path.join(Const.DOWNLOAD_PATH, p['gtvid'] + '.mp3')
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), mp3_file, li, isFolder=False)
        xbmcplugin.endOfDirectory(int(sys.argv[1]), succeeded=True)

    def delete(self, gtvid=None):
        # 削除対象のgtvidをリストアップ
        todelete = [gtvid] if gtvid else list(map(lambda p: p['gtvid'], self.contents()))
        # 削除対象がなければ終了
        if not todelete:
            return
        # ファイル削除
        for gtvid in todelete:
            for filename in ('%s.json', '.%s.json', '%s.mp3', '.%s.mp3'):
                filepath = os.path.join(Const.DOWNLOAD_PATH, filename % gtvid)
                if os.path.isfile(filepath):
                    os.remove(filepath)
        # 設定されているkeyのコンテンツrssファイル生成
        if self.key:
            self.createrss()
        # 全コンテンツのrssファイル生成
        Contents().createrss()

    def createrss(self):
        # RSS設定がない場合は何もしないで終了
        if not self.rssroot:
            return
        # アイテム数
        if self.key:
            limit = None
        else:
            limit = Const.GET('rss_num') or 'unlimited'
            limit = None if limit == 'unlimited' else int(limit)
        #
        # RSSファイルを生成する
        #
        # テンプレート
        header = read_file(os.path.join(Const.TEMPLATE_PATH, 'rss-header.xml'))
        body = read_file(os.path.join(Const.TEMPLATE_PATH, 'rss-body.xml'))
        footer = read_file(os.path.join(Const.TEMPLATE_PATH, 'rss-footer.xml'))
        # RSS生成
        filepath = os.path.join(Const.DOWNLOAD_PATH, self.filename)
        with open(filepath, 'w', encoding='utf-8', errors='ignore') as f:
            # header
            f.write(
                header.format(
                    title='KodiRa - %s' % self.key if self.key else 'KodiRa',
                    image='icon.png',
                    root=self.rssroot))
            # body
            for p in self.contents()[:limit]:  # 開始時間の降順に各番組情報を書き込む
                # title
                title = self.escape(p['title'])
                # source
                source = '%s.mp3' % p['gtvid']
                # file
                mp3_file = os.path.join(Const.DOWNLOAD_PATH, source)
                # date
                date = strptime(p['ft'], '%Y%m%d%H%M%S').strftime('%Y-%m-%d')
                # startdate
                startdate = strptime(p['ft'], '%Y%m%d%H%M%S').strftime('%a, %d %b %Y %H:%M:%S +0900')
                # duration
                duration = int(p['duration'])
                duration = '%02d:%02d:%02d' % (duration // 3600, duration // 60 % 60, duration % 60)
                # filesize
                filesize = os.path.getsize(mp3_file) if os.path.isfile(mp3_file) else 0
                # description
                description = self.escape(p['description'])
                # 各番組情報を書き込む
                f.write(
                    body.format(
                        title=title,
                        gtvid=p['gtvid'],
                        url=p.get('url', ''),
                        root=self.rssroot,
                        source=source,
                        date=date,
                        startdate=startdate,
                        name=p['name'],
                        duration=duration,
                        filesize=filesize,
                        description=description))
            # footer
            f.write(footer)
        #
        # 関係するファイルをダウンロードフォルダにコピーする
        #
        # アイコン画像
        shutil.copy(os.path.join(Const.TEMPLATE_PATH, 'icon.png'), os.path.join(Const.DOWNLOAD_PATH, 'icon.png'))
        # スタイルシート
        shutil.copy(os.path.join(Const.TEMPLATE_PATH, 'stylesheet.xsl'), os.path.join(Const.DOWNLOAD_PATH, 'stylesheet.xsl'))

    def escape(self, text):
        text = unescape(text, entities={'&quot;': '"'})
        text = escape(text, entities={'"': '&quot;'})
        return text
