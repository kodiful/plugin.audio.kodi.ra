# -*- coding: utf-8 -*-

import os
import datetime, time
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
import inspect
import socket

# HTTP接続におけるタイムアウト(秒)
socket.setdefaulttimeout(60)

# addon

addon = xbmcaddon.Addon()

# paths

profile_path      = xbmc.translatePath(addon.getAddonInfo('profile'))
cache_path        = os.path.join(profile_path, 'cache')
media_path        = os.path.join(cache_path, 'media')
data_path         = os.path.join(cache_path, 'data')

plugin_path       = xbmc.translatePath(addon.getAddonInfo('path'))
resources_path    = os.path.join(plugin_path, 'resources')
settings_file     = os.path.join(resources_path, 'settings.xml')
template_path     = os.path.join(resources_path, 'data')
template_file     = os.path.join(template_path, 'settings.xml')
keywords_file     = os.path.join(profile_path, 'keywords.js')
channels_file     = os.path.join(profile_path, 'channels.js')
usersettings_file = os.path.join(profile_path, 'settings.xml')

download_path     = addon.getSetting('download_path')
rss_file          = os.path.join(download_path, 'rss.xml')
exit_file         = os.path.join(download_path, 'exit')

rss_url           = addon.getSetting('rss_url')
if not rss_url.endswith('/'): rss_url = rss_url+'/'

# intervals

resume_timer_interval = 3600
check_interval        = 30
dead_interval         = 30
prep_interval         = 180
margin_interval       = 5
lag                   = 20

# parameters

Resumes = {
    "key":      None,
    "token":    None,
    "area":     None,
    "reinfo":   None,
    "hashinfo": None,
    "reauth":   None,
    "settings": None,
    "keywords": None,
    "update":   None
}

Birth = 0

# others

logo_url = 'http://kodiful.com/KodiRa/downloads/jcba/icon.png'

# utilities

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
    # ログメッセージ
    m = []
    for message in messages:
        if isinstance(message, str):
            m.append(message)
        elif isinstance(message, unicode):
            m.append(message.encode('utf-8'))
        else:
            m.append(str(message))
    message = str('').join(m)
    # ログ書き込み
    if options.get('error', False):
        level = xbmc.LOGERROR
    elif xbmcaddon.Addon().getSetting('debug') == 'true':
        level = xbmc.LOGNOTICE
    else:
        level = None
    if level:
        id = xbmcaddon.Addon().getAddonInfo('id')
        frame = inspect.currentframe(1)
        xbmc.log(str('%s: %s %d: %s') % (id, frame.f_code.co_name, frame.f_lineno, message), level)

def strptime(t, format):
    #startdate = datetime.datetime.strptime(p['startdate'],'%Y-%m-%d %H:%M:%S').strftime('%a, %d %b %Y %H:%M:%S +0000')
    #http://forum.kodi.tv/showthread.php?tid=203759
    try:
        s = datetime.datetime.strptime(t, format)
    except TypeError:
        s = datetime.datetime.fromtimestamp(time.mktime(time.strptime(t, format)))
    return s
