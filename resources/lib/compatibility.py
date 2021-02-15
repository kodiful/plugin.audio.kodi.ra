# -*- coding: utf-8 -*-

from const import *
from common import *
from contents import Contents

import re
import glob

class Compatibility:

    def __init__(self):
        return

    def converter(self):
        status = 0
        status += self.__download_info()
        status += self.__channels_settings()
        status += self.__keywords_settings()
        return status

    def __channels_settings(self):
        status = 0
        file = os.path.join(Const.PROFILE_PATH, 'channels.js')
        if os.path.isfile(file):
            os.rename(file, re.sub(r'\.js$', '.json', file))
            log('convert file: %s' % file)
            status = 1
        return status

    def __keywords_settings(self):
        status = 0
        file = os.path.join(Const.PROFILE_PATH, 'keywords.js')
        if os.path.isfile(file):
            os.rename(file, re.sub(r'\.js$', '.json', file))
            log('convert file: %s' % file)
            status = 1
        return status

    def __download_info(self):
        status = 0
        # jsファイルを検索
        for file in glob.glob(os.path.join(Const.DOWNLOAD_PATH, '*.js')):
            json_file = re.sub(r'\.js$', '.json', file)
            mp3_file = re.sub(r'\.js$', '.mp3', file)
            # 対応するmp3ファイルがある場合は変換する
            if os.path.isfile(mp3_file):
                json = read_json(file)
                p = json['program'][0]
                q = {
                    "description": p['description'],
                    "duration": int(p['duration']),
                    "ft": re.sub(r'[^0-9]', '', p['startdate']),
                    "gtvid": p['gtvid'],
                    "id": p['ch'],
                    "key": p['key'],
                    "name": p['bc'],
                    "stream": '',
                    "title": p['title'],
                    "to": ""
                }
                write_json(json_file, q)
                log('convert file: %s' % file)
            else:
                log('corresponding mp3 file not found: %s' % file)
            # jsファイルを削除
            os.remove(file)
            status = 1
        # shファイルをすべて削除
        for file in glob.glob(os.path.join(Const.DOWNLOAD_PATH, '*.sh')):
            os.remove(file)
        # rssファイルを更新
        if status:
            Contents().createrss()
            #
            # ここで各keyに対するRSSを変換する
            #
        return status
