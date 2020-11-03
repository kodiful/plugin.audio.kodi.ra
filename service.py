# -*- coding: utf-8 -*-

import os
import threading
import xbmc, xbmcgui

from hashlib import md5

from resources.lib.const import Const
from resources.lib.common import *

from resources.lib.cp.radiko import Radiko, getAuthkey, authenticate
from resources.lib.cp.radiru import Radiru
from resources.lib.cp.jcba   import Jcba
from resources.lib.cp.misc   import Misc

from resources.lib.data import Data
from resources.lib.keywords import Keywords

# HTTP接続におけるタイムアウト(秒)
import socket
socket.setdefaulttimeout(60)


class Monitor(xbmc.Monitor):

    def __init__(self, *args, **kwargs):
        self.settings_changed = False
        xbmc.Monitor.__init__(self)

    def onSettingsChanged(self):
        self.settings_changed = True


class Service:

    def __init__(self):
        # ディレクトリをチェック
        if not os.path.isdir(Const.CACHE_PATH): os.makedirs(Const.CACHE_PATH)
        if not os.path.isdir(Const.MEDIA_PATH): os.makedirs(Const.MEDIA_PATH)
        if not os.path.isdir(Const.DATA_PATH):  os.makedirs(Const.DATA_PATH)
        # radiko認証
        self.auth, self.nextauth = self.__authenticate()
        log('radiko authentication initialized.', 'nextauth=', self.nextauth)
        # クラスを初期化
        self.data = self.__update_classes()
        log('class initialized.')
        # 設定ダイアログを生成
        if not os.path.isfile(Const.SETTINGS_FILE):
            self.__settings_setup(self.radiru, self.radiko, self.jcba, self.misc)
            log('settings initialized.')
        # いろいろ初期化
        self.nextaired, self.program_hash, self.settings_hash = self.__update_params()

    def __authenticate(self):
        # radiko認証
        getAuthkey()
        auth = authenticate()
        auth.start()
        while 'authed' not in auth._response or auth._response['authed'] == 0: time.sleep(1)
        if auth._response['area_id'] == '': notify('radiko authentication failed', error=True)
        # 認証情報をファイルに書き込む
        write_json(Const.AUTH_FILE, auth._response)
        # 認証情報と次の更新時刻を返す
        return auth, next_time(Const.AUTH_INTERVAL)

    def __update_classes(self):
        self.radiru = Radiru(renew=True)
        self.radiko = Radiko(area=self.auth._response['area_id'], token=self.auth._response['auth_token'], renew=True)
        self.jcba   = Jcba(renew=True)
        self.misc   = Misc(renew=True)
        return Data((self.radiru, self.radiko, self.jcba, self.misc))

    def __update_params(self):
        # 番組データを取得
        nextaired, program_hash = self.data.setPrograms(renew=True)
        # ユーザ設定のハッシュ
        settings_hash = self.__settings_hash()
        return nextaired, program_hash, settings_hash

    def __settings_hash(self, filepath=Const.USERSETTINGS_FILE):
        settings = read_file(filepath)
        return md5(settings).hexdigest() if settings else ''

    def __settings_setup(self, radiru, radiko, jcba, misc):
        # テンプレート読み込み
        template = read_file(Const.TEMPLATE_FILE)
        # 放送局リスト
        s = [Const.STR(30520)]
        stations = Data((radiru,radiko)).stations
        for station in stations:
            s.append(station['name'])
        # ソース作成
        ffmpeg = os.path.join('usr','local','bin','ffmpeg')
        if not os.path.isfile(ffmpeg): ffmpeg = ''
        source = template.format(
            radiru = radiru.getSettingsData(),
            radiko = radiko.getSettingsData(),
            jcba   = jcba.getSettingsData(),
            misc   = misc.getSettingsData(),
            bc = '|'.join(s),
            ffmpeg = ffmpeg,
            os = platform.system())
        # ファイル書き込み
        write_file(Const.SETTINGS_FILE, source)

    def monitor(self, refresh=False):
        # 開始
        log('enter monitor.')
        # 監視処理開始を通知
        notify('Starting service', time=3000)
        # 監視処理を実行
        monitor = Monitor()
        while not monitor.abortRequested():
            # Const.CHECK_INTERVALの間待機
            if monitor.waitForAbort(Const.CHECK_INTERVAL):
                break
            # 現在時刻
            now = next_time()
            # リセットが検出されたら（設定ダイアログ削除が検出されたら）
            if not os.path.isfile(Const.SETTINGS_FILE):
                # クラスを更新
                self.data = self.__update_classes()
                # 設定ダイアログを生成
                self.__settings_setup(self.radiru, self.radiko, self.jcba, self.misc)
                # いろいろ更新
                self.nextaired, self.program_hash, self.settings_hash = self.__update_params()
                # 画面更新
                refresh = True
                log('settings initialized.')
            # 現在時刻がRadiko認証更新時刻を過ぎていたら
            if now > self.nextauth:
                # radiko認証
                self.auth, self.nextauth = self.__authenticate()
                log('radiko authentication updated.', 'nextauth=', self.nextauth)
                # クラスを更新
                self.radiko = Radiko(area=self.auth._response['area_id'], token=self.auth._response['auth_token'], renew=True)
                self.data   = Data((self.radiru, self.radiko, self.jcba, self.misc))
                log('class updated.')
            # 現在時刻が更新予定時刻を過ぎていたら
            if now > self.nextaired:
                # 番組データを取得
                self.nextaired, new_hash = self.data.setPrograms(renew=True)
                #　番組データが更新されたら
                if new_hash != self.program_hash:
                    self.program_hash = new_hash
                    # ダウンロードする番組を抽出
                    self.data.matchPrograms()
                    # 画面更新
                    refresh = True
                    log('program updated.')
                else:
                    log('pending program update.', 'nextaired=', self.nextaired)
            # ダウンロードする番組が検出されたら
            if self.data.matched_programs:
                # ダウンロードに追加
                self.data.addDownload()
            # 設定更新が検出されたら
            if monitor.settings_changed:
                new_hash = self.__settings_hash()
                if new_hash != self.settings_hash:
                    self.settings_hash = new_hash
                    # 画面更新
                    refresh = True
                    log('settings changed.')
                else:
                    log('settings unchanged.')
                monitor.settings_changed = False
            # 画面更新が検出されたら
            if refresh:
                # カレントウィンドウをチェック
                if xbmcgui.getCurrentWindowDialogId() == 9999:
                    path = xbmc.getInfoLabel('Container.FolderPath')
                    argv = 'plugin://%s/' % Const.ADDON_ID
                    if (path == argv and Const.GET('download') == 'false') or (path == '%s?action=showPrograms' % argv):
                        xbmc.executebuiltin('Container.Update(%s?action=showPrograms,replace)' % argv)
                        refresh = False
        # 終了
        log('exit monitor.')


if __name__  == '__main__': Service().monitor()
