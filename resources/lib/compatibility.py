# -*- coding: utf-8 -*-

from .const import Const
from .common import *
from .rss import RSS

import re
import glob

class Compatibility:

    def __init__(self):
        return

    def converter(self):
        status = 0
        status += self.__download_info()
        status += self.__channels_config()
        status += self.__keywords_config()
        return status

    def __channels_config(self):
        status = 0
        file = os.path.join(Const.PROFILE_PATH, 'channels.js')
        if os.path.isfile(file):
            os.rename(file, re.sub(r'\.js$', '.json', file))
            log('%s converted' % file)
            status = 1
        return status

    def __keywords_config(self):
        status = 0
        file = os.path.join(Const.PROFILE_PATH, 'keywords.js')
        if os.path.isfile(file):
            os.rename(file, re.sub(r'\.js$', '.json', file))
            log('%s converted' % file)
            status = 1
        return status

    def __download_info(self):
        status = 0
        for file in glob.glob(os.path.join(Const.DOWNLOAD_PATH, '*.js')):
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
                "source": "",
                "title": p['title'],
                "to": ""
            }
            write_json(re.sub(r'\.js$', '.json', file), q)
            os.remove(file)
            log('%s converted' % file)
            status = 1
        if status: RSS().create()
        return status
