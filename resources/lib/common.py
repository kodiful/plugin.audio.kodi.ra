# -*- coding: utf-8 -*-

import os
import datetime, time
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
import inspect
import socket

# HTTP接続におけるタイムアウト(秒)
socket.setdefaulttimeout(60)

# addon

__addon__ = xbmcaddon.Addon()

# paths

__profile_path__ = xbmc.translatePath(__addon__.getAddonInfo('profile'))
__cache_path__   = os.path.join(__profile_path__, 'cache')
__media_path__   = os.path.join(__cache_path__, 'media')
__data_path__    = os.path.join(__cache_path__, 'data')

__plugin_path__       = xbmc.translatePath(__addon__.getAddonInfo('path'))
__resources_path__    = os.path.join(__plugin_path__, 'resources')
__settings_file__     = os.path.join(__resources_path__, 'settings.xml')
__template_path__     = os.path.join(__resources_path__, 'data')
__template_file__     = os.path.join(__template_path__, 'settings.xml')
__keywords_file__     = os.path.join(__profile_path__, 'keywords.js')
__channels_file__     = os.path.join(__profile_path__, 'channels.js')
__usersettings_file__ = os.path.join(__profile_path__, 'settings.xml')

__download_path__ = __addon__.getSetting('download_path')
__rss_file__      = os.path.join(__download_path__, 'rss.xml')
__exit_file__     = os.path.join(__download_path__, 'exit')
__rss_url__       = __addon__.getSetting('rss_url')
if not __rss_url__.endswith('/'): __rss_url__ = __rss_url__+'/'

# intervals

__resume_timer_interval__ = 3600
__check_interval__        = 30
__dead_interval__         = 30
__prep_interval__         = 180
__margin_interval__       = 5
__lag__                   = 20

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

__logo_url__ = 'http://kodiful.com/KodiRa/downloads/jcba/icon.png'

# utilities

def notify(message, time=10000, image='DefaultIconError.png'):
    if message:
        xbmc.executebuiltin('Notification("KodiRa","%s",%d,"%s")' % (message,time,image))

def notify2(result, onlyonerror=True):
    if result['status']:
        if not onlyonerror: notify(result['message'],image='DefaultIconInfo.png')
    else:
        notify(result['message'],image='DefaultIconError.png')

def log(*messages, **options):
    addon = xbmcaddon.Addon()
    if options.get('error', False):
        level = xbmc.LOGERROR
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
                m.append(str(message))
        frame = inspect.currentframe(1)
        xbmc.log(str('%s: %s %d: %s') % (addon.getAddonInfo('id'), frame.f_code.co_name, frame.f_lineno, str('').join(m)), level)

def strptime(t, format):
    #startdate = datetime.datetime.strptime(p['startdate'],'%Y-%m-%d %H:%M:%S').strftime('%a, %d %b %Y %H:%M:%S +0000')
    #http://forum.kodi.tv/showthread.php?tid=203759
    try:
        s = datetime.datetime.strptime(t, format)
    except TypeError:
        s = datetime.datetime.fromtimestamp(time.mktime(time.strptime(t, format)))
    return s
