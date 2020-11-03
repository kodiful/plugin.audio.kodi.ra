# -*- coding: utf-8 -*-

from const import Const
from common import *

import os
import glob
import shutil


class Params:
    # RSS設定
    ENABLED  = Const.GET('rss')
    # ファイルパス
    RSS_FILE = os.path.join(Const.DOWNLOAD_PATH, 'rss.xml')
    # URL
    RSS_URL  = Const.GET('rss_url')
    if not RSS_URL.endswith('/'): RSS_URL = RSS_URL+'/'


class RSS:

    def __init__(self):
        return

    def create(self):
        if Const.GET('rss') == 'false': return
        # テンプレート
        header = read_file(os.path.join(Const.TEMPLATE_PATH,'rss-header.xml'))
        body = read_file(os.path.join(Const.TEMPLATE_PATH,'rss-body.xml'))
        footer = read_file(os.path.join(Const.TEMPLATE_PATH,'rss-footer.xml'))
        # RSSファイルを生成する
        with open(Params.RSS_FILE, 'w') as f:
            # header
            f.write(
                header.format(
                    image=Params.RSS_URL+'icon.png')
                )
            # body
            plist = []
            for file in glob.glob(os.path.join(Const.DOWNLOAD_PATH, '*.json')):
                json_file = os.path.join(Const.DOWNLOAD_PATH, file)
                mp3_file = os.path.join(Const.DOWNLOAD_PATH, file.replace('.json','.mp3'))
                if os.path.isfile(mp3_file):
                    plist.append(read_json(json_file))
                else:
                    log('lost file=', mp3_file)
            # 開始時間の降順に各番組情報を書き込む
            for p in sorted(plist, key=lambda item: item['ft'], reverse=True):
                # gtvid
                gtvid = p['gtvid']
                # url
                url = Params.RSS_URL + gtvid + '.mp3'
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
                        title=p['title'],
                        gtvid=gtvid,
                        url=url,
                        startdate=startdate,
                        bc=p['name'],
                        duration=duration,
                        filesize=filesize,
                        description=p['description']))
            # footer
            f.write(footer)
        # アイコン画像がRSSから参照できるように、画像をダウンロードフォルダにコピーする
        iconpath = os.path.join(Const.DOWNLOAD_PATH, 'icon.png')
        if not os.path.isfile(iconpath):
            shutil.copy(os.path.join(Const.PLUGIN_PATH, 'icon.png'), iconpath)
        # copy script if necessary
        phppath = os.path.join(Const.DOWNLOAD_PATH, 'rss.php')
        if not os.path.isfile(phppath):
            shutil.copy(os.path.join(Const.TEMPLATE_PATH, 'rss.php'), phppath)
