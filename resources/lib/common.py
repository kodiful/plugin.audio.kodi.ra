# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os
import datetime, time
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
import inspect
import socket

# HTTP接続におけるタイムアウト(秒)
socket.setdefaulttimeout(60)

# addon info

__addon_id__ = 'plugin.audio.kodi.ra'
__settings__ = xbmcaddon.Addon(__addon_id__)

# paths

__profile_path__ = xbmc.translatePath(__settings__.getAddonInfo('profile'))
__cache_path__   = os.path.join(__profile_path__, 'cache')
__media_path__   = os.path.join(__cache_path__, 'media')
__data_path__    = os.path.join(__cache_path__, 'data')

if not os.path.isdir(__cache_path__): os.makedirs(__cache_path__)
if not os.path.isdir(__media_path__): os.makedirs(__media_path__)
if not os.path.isdir(__data_path__):  os.makedirs(__data_path__)

__plugin_path__       = xbmc.translatePath(__settings__.getAddonInfo('path'))
__resources_path__    = os.path.join(__plugin_path__, 'resources')
__settings_file__     = os.path.join(__resources_path__, 'settings.xml')
__template_path__     = os.path.join(__resources_path__, 'data')
__template_file__     = os.path.join(__template_path__, 'settings.xml')
__keywords_file__     = os.path.join(__profile_path__, 'keywords.js')
__usersettings_file__ = os.path.join(__profile_path__, 'settings.xml')

__download_path__ = __settings__.getSetting('download_path')
__rss_file__      = os.path.join(__download_path__, 'rss.xml')
__exit_file__     = os.path.join(__download_path__, 'exit')
__rss_url__       = __settings__.getSetting('rss_url')
if not __rss_url__.endswith('/'): __rss_url__ = __rss_url__+'/'

# intervals

__resume_timer_interval__ = 3600
__check_interval__        = 30
__dead_interval__         = 30
__prep_interval__         = 180
__margin_interval__       = 5

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

__logo_url__ = 'http://kodiful.com/KodiRa/downloads/simul/icon.png'

# utilities

def notify(message, time=10000, image='DefaultIconError.png'):
    if message:
        xbmc.executebuiltin('XBMC.Notification("KodiRa","%s",%d,"%s")' % (message,time,image))

def notify2(result, onlyonerror=True):
    if result['status']:
        if not onlyonerror: notify(result['message'],image='DefaultIconInfo.png')
    else:
        notify(result['message'],image='DefaultIconError.png')

def log(*messages):
    if True or __settings__.getSetting('debug') == 'true':
        m = []
        for message in messages:
            if isinstance(message, str):
                m.append(message)
            elif isinstance(message, unicode):
                m.append(message.encode('utf-8'))
            else:
                m.append(str(message))
        frame = inspect.currentframe(1)
        xbmc.log(str('KodiRa: %s %d: %s') % (frame.f_code.co_name, frame.f_lineno, str('').join(m)))

def strptime(t, format):
    #startdate = datetime.datetime.strptime(p['startdate'],'%Y-%m-%d %H:%M:%S').strftime('%a, %d %b %Y %H:%M:%S +0000')
    #http://forum.kodi.tv/showthread.php?tid=203759
    try:
        s = datetime.datetime.strptime(t, format)
    except TypeError:
        s = datetime.datetime.fromtimestamp(time.mktime(time.strptime(t, format)))
    return s
