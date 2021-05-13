# -*- coding: utf-8 -*-

import os
import datetime
import time
import inspect
import json
import urllib
import chardet

import xbmc
import xbmcaddon


# file i/o

def read_file(filepath):
    if os.path.isfile(filepath) and os.path.getsize(filepath) > 0:
        with open(filepath, 'rb') as f:
            data = f.read()
        encoding = chardet.detect(data)['encoding']
        if encoding:
            data = data.decode(encoding=encoding, errors='ignore')
        return data
    else:
        return None


def write_file(filepath, data):
    if isinstance(data, bytes):
        with open(filepath, 'wb') as f:
            f.write(data)
    elif isinstance(data, str):
        with open(filepath, 'w', encoding='utf-8', errors='ignore') as f:
            f.write(data)
    else:
        raise TypeError


def read_json(filepath):
    data = read_file(filepath)
    if data:
        try:
            return json.loads(data)
        except ValueError as e:
            log(filepath, str(e), error=True)
            return None
    else:
        return None


def write_json(filepath, data):
    write_file(filepath, json.dumps(data, sort_keys=True, ensure_ascii=False, indent=4))


def urlread(url, headers={}, params={}):
    opener = urllib.request.build_opener()
    h = [('User-Agent', 'Mozilla/5.0')]  # User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:68.0) Gecko/20100101 Firefox/68.0
    for key, val in headers.items():
        h.append((key, val))
    opener.addheaders = h
    if params:
        url = url + '?' + urllib.parse.urlencode(params)
    # log('url(Full): %s' % url)
    try:
        response = opener.open(url)
        buf = response.read()
        response.close()
    except urllib.request.HTTPError as e:
        log('HTTPError url:{url}, code:{code}'.format(url=url, code=e.code), error=True)
        buf = ''
    except urllib.error.URLError as e:
        log('URLError url:{url}, reason:{reason}'.format(url=url, reason=e.reason), error=True)
        buf = ''
    except Exception as e:
        log(url, str(e), error=True)
        buf = ''
    return buf


# datetime utilities

def timestamp(seconds=0):
    t = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
    return t.strftime('%Y%m%d%H%M%S')


def strptime(t, format):
    # startdate = datetime.datetime.strptime(p['startdate'],'%Y-%m-%d %H:%M:%S').strftime('%a, %d %b %Y %H:%M:%S +0000')
    # http://forum.kodi.tv/showthread.php?tid=203759
    try:
        s = datetime.datetime.strptime(t, format)
    except TypeError:
        s = datetime.datetime.fromtimestamp(time.mktime(time.strptime(t, format)))
    return s


# workaround for encode problems for strftime on Windows
# cf. https://ja.stackoverflow.com/questions/44597/windows上のpythonのdatetime-strftimeで日本語を使うとエラーになる
def strftime(d, format):
    return d.strftime(format.encode('unicode-escape').decode()).encode().decode('unicode-escape')


# other utilities

def notify(message, **options):
    # アドオン
    addon = xbmcaddon.Addon()
    # ポップアップする時間
    time = options.get('time', 10000)
    # ポップアップアイコン
    image = options.get('image', None)
    if image:
        pass
    elif options.get('error', False):
        image = 'DefaultIconError.png'
    else:
        image = 'DefaultIconInfo.png'
    # ログ出力
    log(message, error=options.get('error', False))
    # ポップアップ通知
    xbmc.executebuiltin('Notification("%s","%s",%d,"%s")' % (addon.getAddonInfo('name'), message, time, image))


def log(*messages, **options):
    # アドオン
    addon = xbmcaddon.Addon()
    # ログレベルを設定
    if options.get('error', False):
        level = xbmc.LOGERROR
    elif options.get('notice', False):
        level = xbmc.LOGINFO
    elif addon.getSetting('debug') == 'true':
        level = xbmc.LOGINFO
    else:
        level = None
    # ログ出力
    if level:
        frame = inspect.currentframe().f_back
        xbmc.log('%s: %s(%d): %s: %s' % (
            addon.getAddonInfo('id'),
            os.path.basename(frame.f_code.co_filename),
            frame.f_lineno,
            frame.f_code.co_name,
            ' '.join(map(lambda x: str(x), messages))
        ), level)
