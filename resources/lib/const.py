# -*- coding: utf-8 -*-

import os
import xbmc, xbmcaddon


class Const:

    # addon
    ADDON = xbmcaddon.Addon()
    ADDON_ID = ADDON.getAddonInfo('id')

    GET = ADDON.getSetting
    SET = ADDON.setSetting

    #STR = ADDON.getLocalizedString
    @staticmethod
    def STR(id): return Const.ADDON.getLocalizedString(id).encode('utf-8')

    # paths
    PROFILE_PATH      = xbmc.translatePath(ADDON.getAddonInfo('profile'))
    CACHE_PATH        = os.path.join(PROFILE_PATH, 'cache')
    MEDIA_PATH        = os.path.join(CACHE_PATH, 'media')
    DATA_PATH         = os.path.join(CACHE_PATH, 'data')
    AUTH_FILE         = os.path.join(DATA_PATH, 'auth.json')
    STATUS_FILE       = os.path.join(DATA_PATH, 'status.json')

    PLUGIN_PATH       = xbmc.translatePath(ADDON.getAddonInfo('path'))
    RESOURCES_PATH    = os.path.join(PLUGIN_PATH, 'resources')
    SETTINGS_FILE     = os.path.join(RESOURCES_PATH, 'settings.xml')
    TEMPLATE_PATH     = os.path.join(RESOURCES_PATH, 'data')
    TEMPLATE_FILE     = os.path.join(TEMPLATE_PATH, 'settings.xml')
    KEYWORDS_FILE     = os.path.join(PROFILE_PATH, 'keywords.json')
    CHANNELS_FILE     = os.path.join(PROFILE_PATH, 'channels.json')
    USERSETTINGS_FILE = os.path.join(PROFILE_PATH, 'settings.xml')

    DOWNLOAD_PATH     = GET('download_path')

    # database
    DB_PATH           = xbmc.translatePath('special://database')
    CACHE_DB          = os.path.join(DB_PATH, 'Textures13.db')

    # intervals
    AUTH_INTERVAL     = 3600
    CHECK_INTERVAL    = 30
    PREP_INTERVAL     = 180
    MARGIN_INTERVAL   = 5

    # others
    LOGO_URL          = 'http://kodiful.com/KodiRa/downloads/jcba/icon.png'
