# -*- coding: utf-8 -*-

from const import Const
from common import *

import sys
import os
import glob
import shutil

from hashlib import md5
from xml.sax.saxutils import escape, unescape


class RSS:

    def __init__(self):
        # for backward compatibility
        if Const.GET('rss') == 'false': Const.SET('rss', '0')
        # rss root
        self.rss_root  = os.path.dirname(Const.GET('rss_url'))

    def key2name(self, key):
        return md5(key).hexdigest()

    def key2file(self, key=''):
        return 'rss_%s.xml' % self.key2name(key) if key else 'rss.xml'

    def key2url(self, key=''):
        return '%s/%s' % (self.rss_root, self.key2file(key)) if self.rss_root else ''

    def create(self, key=None):
        # テンプレート
        header = read_file(os.path.join(Const.TEMPLATE_PATH, 'rss-header.xml'))
        body = read_file(os.path.join(Const.TEMPLATE_PATH, 'rss-body.xml'))
        footer = read_file(os.path.join(Const.TEMPLATE_PATH, 'rss-footer.xml'))
        # RSSファイルパス、アイテム数
        filepath = os.path.join(Const.DOWNLOAD_PATH, self.key2file(key))
        if key:
            limit = None
        else:
            limit = Const.GET('rss')
            limit = None if limit == 'unlimited' else int(limit)
        # RSSファイルを生成する
        with open(filepath, 'w') as f:
            # header
            f.write(
                header.format(
                    title=key or 'KodiRa',
                    image='icon.png',
                    root=self.rss_root))
            # body
            contents = []
            for file in glob.glob(os.path.join(Const.DOWNLOAD_PATH, '*.json')):
                json_file = file
                mp3_file = file.replace('.json', '.mp3')
                if os.path.isfile(mp3_file):
                    contents.append(read_json(json_file))
            # keyが指定されていたらフィルタ
            if key: contents = filter(lambda p: p['key']==key, contents)
            # 開始時間の降順に各番組情報を書き込む
            for p in sorted(contents, key=lambda item: item['ft'], reverse=True)[:limit]:
                # title
                title = self.escape(p['title'])
                # source
                source = '%s.mp3' % p['gtvid']
                # file
                mp3_file = os.path.join(Const.DOWNLOAD_PATH, source)
                # startdate
                startdate = strptime(p['ft'],'%Y%m%d%H%M%S').strftime('%a, %d %b %Y %H:%M:%S +0900')
                # duration
                duration = int(p['duration'])
                duration = '%02d:%02d:%02d' % (int(duration/3600),int(duration/60)%60,duration%60)
                # filesize
                filesize = os.path.getsize(mp3_file) if os.path.isfile(mp3_file) else 0
                # description
                description = self.escape(p['description'])
                # 各番組情報を書き込む
                f.write(
                    body.format(
                        title=title,
                        gtvid=p['gtvid'],
                        url=p.get('url',''),
                        root=self.rss_root,
                        source=source,
                        startdate=startdate,
                        name=p['name'],
                        duration=duration,
                        filesize=filesize,
                        description=description))
            # footer
            f.write(footer)
        # アイコン画像がRSSから参照できるように、画像をダウンロードフォルダにコピーする
        shutil.copy(os.path.join(Const.PLUGIN_PATH, 'icon.png'), os.path.join(Const.DOWNLOAD_PATH, 'icon.png'))
        # copy stylesheet
        shutil.copy(os.path.join(Const.TEMPLATE_PATH, 'stylesheet.xsl'), os.path.join(Const.DOWNLOAD_PATH, 'stylesheet.xsl'))

    def escape(self, text):
        text = unescape(text, entities={'&quot;':'"'})
        text = escape(text, entities={'"':'&quot;'})
        return text
