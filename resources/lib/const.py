# -*- coding: utf-8 -*-

import os

import xbmcaddon
import xbmcvfs


class Const:

    # addon
    ADDON = xbmcaddon.Addon()
    ADDON_ID = ADDON.getAddonInfo('id')
    ADDON_NAME = ADDON.getAddonInfo('name')

    GET = ADDON.getSetting
    SET = ADDON.setSetting
    STR = ADDON.getLocalizedString

    # paths
    PROFILE_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
    CACHE_PATH = os.path.join(PROFILE_PATH, 'cache')
    MEDIA_PATH = os.path.join(CACHE_PATH, 'media')
    DATA_PATH = os.path.join(CACHE_PATH, 'data')
    AUTH_FILE = os.path.join(DATA_PATH, 'auth.json')
    STATUS_FILE = os.path.join(DATA_PATH, 'status.json')

    PLUGIN_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
    RESOURCES_PATH = os.path.join(PLUGIN_PATH, 'resources')
    SETTINGS_FILE = os.path.join(RESOURCES_PATH, 'settings.xml')
    TEMPLATE_PATH = os.path.join(RESOURCES_PATH, 'data')
    TEMPLATE_FILE = os.path.join(TEMPLATE_PATH, 'settings.xml')
    LOGO_PATH = os.path.join(TEMPLATE_PATH, 'cp', 'logo')
    KEYWORDS_FILE = os.path.join(PROFILE_PATH, 'keywords.json')
    CHANNELS_FILE = os.path.join(PROFILE_PATH, 'channels.json')
    USERSETTINGS_FILE = os.path.join(PROFILE_PATH, 'settings.xml')

    QUEUE_FILE = os.path.join(DATA_PATH, 'queue.json')
    LOG_FILE = os.path.join(DATA_PATH, 'download.log')
    DOWNLOAD_PATH = GET('download_path')

    # database
    DB_PATH = xbmcvfs.translatePath('special://database')
    CACHE_DB = os.path.join(DB_PATH, 'Textures13.db')

    # intervals
    AUTH_INTERVAL = 3600
    CHECK_INTERVAL = 30
    PREP_INTERVAL = 180
    MARGIN_INTERVAL = 5

    # others
    LOGO_FILE = os.path.join(TEMPLATE_PATH, 'icon.png')
