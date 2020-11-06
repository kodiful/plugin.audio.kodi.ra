# -*- coding: utf-8 -*-

import os
import datetime, time
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
import inspect
import urllib2
import json
import re


# workaround for encoding problems

def convert(obj, strip=False):
    if isinstance(obj, dict):
        obj1 = {}
        for key, val in obj.items():
            obj1[convert(key)] = convert(val, strip)
        return obj1
    elif isinstance(obj, list):
        return map(lambda x: convert(x, strip), obj)
    elif isinstance(obj, unicode):
        return convert(obj.encode('utf-8'), strip)
    elif isinstance(obj, str):
        if strip:
            obj = re.sub(r'(?:　|\r\n|\n|\t)', ' ', obj) # 全角スペース、改行、タブを半角スペースに置換
            obj = re.sub(r'\s{2,}',            ' ', obj) # 二つ以上続く半角スペースは一つに置換
            obj = re.sub(r'(^\s+|\s+$)',        '', obj) # 先頭と末尾の半角スペースを削除
        return obj
    else:
        return obj


# file i/o

def read_file(filepath):
    if os.path.isfile(filepath) and os.path.getsize(filepath) > 0:
        with open(filepath, 'r') as f:
            return f.read()
    else:
        return None

def write_file(filepath, data):
    with open(filepath, 'w') as f:
        return f.write(data)

def read_json(filepath):
    if os.path.isfile(filepath) and os.path.getsize(filepath) > 0:
        with open(filepath, 'r') as f:
            data  = json.loads(f.read())
        return convert(data)
    else:
        return None

def write_json(filepath, data):
    with open(filepath, 'w') as f:
        f.write(json.dumps(data, sort_keys=True, ensure_ascii=False, indent=4))

def urlread(url, *headers):
    opener = urllib2.build_opener()
    h = [('User-Agent', 'Mozilla/5.0')] # User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:68.0) Gecko/20100101 Firefox/68.0
    for header in headers:
        h.append(header)
    opener.addheaders = h
    try:
        response = opener.open(url)
        buf = response.read()
        response.close()
    except urllib2.HTTPError, e:
        log('HTTPError url:{url}, code:{code}, reason:{reason}, error={error}'.format(
            url=url, code=e.code, reason=e.reason, error=e.read()), error=True)
        buf = ''
    return buf.encode('utf-8') if isinstance(buf,unicode) else buf


# datetime utilities

def nexttime(seconds=0):
    now = datetime.datetime.now()
    nexttime = now + datetime.timedelta(seconds=seconds)
    return nexttime.strftime('%Y%m%d%H%M%S')

# workaround for encode problems for strftime on Windows
def strftime(d, format):
    if isinstance(format, unicode):
        return d.strftime(format.encode('unicode-escape')).decode('unicode-escape')
    else:
        return d.strftime(format)

def strptime(t, format):
    #startdate = datetime.datetime.strptime(p['startdate'],'%Y-%m-%d %H:%M:%S').strftime('%a, %d %b %Y %H:%M:%S +0000')
    #http://forum.kodi.tv/showthread.php?tid=203759
    try:
        s = datetime.datetime.strptime(t, format)
    except TypeError:
        s = datetime.datetime.fromtimestamp(time.mktime(time.strptime(t, format)))
    return s


# other utilities

def notify(message, **options):
    time = options.get('time', 10000)
    image = options.get('image', None)
    if image is None:
        if options.get('error', False):
            image = 'DefaultIconError.png'
        else:
            image = 'DefaultIconInfo.png'
    log(message, error=options.get('error', False))
    xbmc.executebuiltin('Notification("%s","%s",%d,"%s")' % (xbmcaddon.Addon().getAddonInfo('name'),message,time,image))

def log(*messages, **options):
    addon = xbmcaddon.Addon()
    if options.get('error', False):
        level = xbmc.LOGERROR
    elif options.get('notice', False):
        level = xbmc.LOGNOTICE
    elif addon.getSetting('debug') == 'true':
        level = xbmc.LOGNOTICE
    else:
        level = None
    if level:
        m = []
        for message in messages:
            if isinstance(message, str):
                m.append(message)
            elif isinstance(message, unicode):
                m.append(message.encode('utf-8'))
            else:
                #m.append(str(message))
                m.append(json.dumps(message, sort_keys=True, ensure_ascii=False, indent=4))
        frame = inspect.currentframe(1)
        xbmc.log(str('%s: %s(%d): %s: %s') % (addon.getAddonInfo('id'), os.path.basename(frame.f_code.co_filename), frame.f_lineno, frame.f_code.co_name, str(' ').join(m)), level)
