# -*- coding: utf-8 -*-

from const import Const
from common import *

import os
import glob
import shutil

from xml.sax.saxutils import escape, unescape


class Params:
    # ファイルパス
    RSS_FILE = os.path.join(Const.DOWNLOAD_PATH, 'rss.xml')


class RSS:

    def __init__(self):
        # for backward compatibility
        if Const.GET('rss') == 'false': Const.SET('rss', '0')

    def create(self):
        if Const.GET('rss') == '0': return
        # テンプレート
        header = read_file(os.path.join(Const.TEMPLATE_PATH,'rss-header.xml'))
        body = read_file(os.path.join(Const.TEMPLATE_PATH,'rss-body.xml'))
        footer = read_file(os.path.join(Const.TEMPLATE_PATH,'rss-footer.xml'))
        # rssファイルを生成する
        with open(Params.RSS_FILE, 'w') as f:
            # header
            f.write(header.format(image='icon.png'))
            # body
            plist = []
            for file in glob.glob(os.path.join(Const.DOWNLOAD_PATH, '*.json')):
                json_file = file
                mp3_file = file.replace('.json', '.mp3')
                if os.path.isfile(mp3_file):
                    plist.append(read_json(json_file))
            # 開始時間の降順に各番組情報を書き込む
            limit = Const.GET('rss')
            limit = None if limit == 'unlimited' else int(limit)
            for p in sorted(plist, key=lambda item: item['ft'], reverse=True)[:limit]:
                # gtvid
                gtvid = p['gtvid']
                # source
                source = gtvid + '.mp3'
                # file
                mp3_file = os.path.join(Const.DOWNLOAD_PATH, gtvid + '.mp3')
                # startdate
                startdate = strptime(p['ft'],'%Y%m%d%H%M%S').strftime('%a, %d %b %Y %H:%M:%S +0900')
                # duration
                duration = int(p['duration'])
                duration = '%02d:%02d:%02d' % (int(duration/3600),int(duration/60)%60,duration%60)
                # filesize
                filesize = os.path.getsize(mp3_file) if os.path.isfile(mp3_file) else 0
                # 各番組情報を書き込む
                f.write(
                    body.format(
                        title=escape(unescape(p['title'], entities={'&quot;':'"'}), entities={'"':'&quot;'}),
                        gtvid=gtvid,
                        url=p.get('url',''),
                        source=source,
                        startdate=startdate,
                        name=p['name'],
                        duration=duration,
                        filesize=filesize,
                        description=escape(unescape(p['description'], entities={'&quot;':'"'}), entities={'"':'&quot;'})
                    )
                )
            # footer
            f.write(footer)
        # アイコン画像がRSSから参照できるように、画像をダウンロードフォルダにコピーする
        shutil.copy(os.path.join(Const.PLUGIN_PATH, 'icon.png'), os.path.join(Const.DOWNLOAD_PATH, 'icon.png'))
        # copy stylesheet
        shutil.copy(os.path.join(Const.TEMPLATE_PATH, 'stylesheet.xsl'), os.path.join(Const.DOWNLOAD_PATH, 'stylesheet.xsl'))
        # copy php script
        shutil.copy(os.path.join(Const.TEMPLATE_PATH, 'rss.php'), os.path.join(Const.DOWNLOAD_PATH, 'rss.php'))
