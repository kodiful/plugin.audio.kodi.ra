# -*- coding: utf-8 -*-

import os
import xbmc, xbmcaddon

# addon info

__addon_id__ = 'plugin.audio.kodi.ra'
__settings__ = xbmcaddon.Addon(__addon_id__)

# paths

__profile_path__ = xbmc.translatePath(__settings__.getAddonInfo('profile').decode('utf-8'))
__cache_path__   = os.path.join(__profile_path__, 'cache')
__media_path__   = os.path.join(__cache_path__, 'media')
__data_path__    = os.path.join(__cache_path__, 'data')

if not os.path.isdir(__cache_path__): os.makedirs(__cache_path__)
if not os.path.isdir(__media_path__): os.makedirs(__media_path__)
if not os.path.isdir(__data_path__):  os.makedirs(__data_path__)

__plugin_path__    = xbmc.translatePath(__settings__.getAddonInfo('path').decode('utf-8'))
__settings_file__  = os.path.join(__plugin_path__, 'resources', 'settings.xml')
__template_file__  = os.path.join(__plugin_path__, 'resources', 'data', 'settings.xml')
__usersettings_file__ = os.path.join(__profile_path__, 'settings.xml')

# intervals

__resume_timer_interval__ = 3600
__check_interval__        = 60
__dead_interval__         = 5

# utilities

def notify(message, time=10000, image='DefaultIconError.png'):
    xbmc.executebuiltin('XBMC.Notification("KodiRa","%s",%d,"%s")' % (message,time,image))
