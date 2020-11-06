# -*- coding: utf-8 -*-

from resources.lib.const import Const
from resources.lib.common import *
from resources.lib.compatibility import Compatibility

import os
import platform
import threading
import xbmc, xbmcgui

from hashlib import md5

from resources.lib.cp.radiko import Radiko, Authkey, Authenticate
from resources.lib.cp.radiru import Radiru
from resources.lib.cp.jcba   import Jcba
from resources.lib.cp.misc   import Misc

from resources.lib.programs  import Programs
from resources.lib.keywords  import Keywords

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
        # 古い形式ののファイルの変換
        status = Compatibility().converter()
        # 古い形式のファイルが更新されたときは設定ダイアログを再作成
        if status:
            os.remove(Const.SETTINGS_FILE)
            notify('Settings updated')
        # ディレクトリをチェック
        if not os.path.isdir(Const.CACHE_PATH): os.makedirs(Const.CACHE_PATH)
        if not os.path.isdir(Const.MEDIA_PATH): os.makedirs(Const.MEDIA_PATH)
        if not os.path.isdir(Const.DATA_PATH):  os.makedirs(Const.DATA_PATH)
        # radiko認証
        self.nextauth = self.authenticate()
        log('radiko authentication initialized. nextauth:{t}'.format(t=self.nextauth))
        # クラスを初期化
        self.update_classes()
        # いろいろ初期化
        self.nextaired, self.program_hash, self.settings_hash = self.update_params()
        # 設定ダイアログがなければ作成
        if not os.path.isfile(Const.SETTINGS_FILE):
            self.setup_settings()
            log('settings initialized.')

    def authenticate(self):
        # radiko認証
        Authkey()
        auth = Authenticate()
        if auth.response['area_id'] == '': notify('radiko authentication failed', error=True)
        # 認証情報をファイルに書き込む
        self.auth = auth.response
        write_json(Const.AUTH_FILE, self.auth)
        # 次の更新時刻を返す
        return nexttime(Const.AUTH_INTERVAL)

    def update_classes(self):
        self.radiru = Radiru(renew=True)
        self.radiko = Radiko(area=self.auth['area_id'], token=self.auth['auth_token'], renew=True)
        self.jcba = Jcba(renew=True)
        self.misc = Misc(renew=True)
        self.programs = Programs((self.radiru, self.radiko, self.jcba, self.misc))

    def update_params(self):
        # 番組データを取得
        nextaired, program_hash = self.programs.setup(renew=True)
        # ユーザ設定のハッシュ
        settings_hash = self.hash_settings()
        return nextaired, program_hash, settings_hash

    def hash_settings(self):
        settings = read_file(Const.USERSETTINGS_FILE)
        return md5(settings).hexdigest() if settings else ''

    def setup_settings(self):
        # テンプレート読み込み
        template = read_file(Const.TEMPLATE_FILE)
        # 放送局リスト
        s = [Const.STR(30520)]
        stations = Programs((self.radiru,self.radiko)).stations
        for station in stations:
            s.append(station['name'])
        # ソース作成
        source = template.format(
            radiru = self.radiru.getSettingsData(),
            radiko = self.radiko.getSettingsData(),
            jcba   = self.jcba.getSettingsData(),
            misc   = self.misc.getSettingsData(),
            bc = '|'.join(s),
            ffmpeg = '',
            os = platform.system())
        # ファイル書き込み
        write_file(Const.SETTINGS_FILE, source)

    def monitor(self, refresh=False):
        # 開始
        log('enter monitor.')
        # 監視処理開始を通知
        notify('Starting service')
        # 監視処理を実行
        monitor = Monitor()
        while not monitor.abortRequested():
            # Const.CHECK_INTERVALの間待機
            if monitor.waitForAbort(Const.CHECK_INTERVAL):
                break
            # 現在時刻
            now = nexttime()
            # リセットが検出されたら（設定ダイアログ削除が検出されたら）
            if not os.path.isfile(Const.SETTINGS_FILE):
                # クラスを更新
                self.update_classes()
                # いろいろ更新
                self.nextaired, self.program_hash, self.settings_hash = self.update_params()
                # 設定ダイアログを生成
                self.setup_settings()
                # 画面更新
                refresh = True
                log('settings initialized.')
            # 現在時刻がRadiko認証更新時刻を過ぎていたら
            if now > self.nextauth:
                # radiko認証
                self.nextauth = self.authenticate()
                log('radiko authentication updated. nextauth:{t}'.format(t=self.nextauth))
                # クラスを更新
                self.radiko = Radiko(area=self.auth['area_id'], token=self.auth['auth_token'], renew=True)
                self.programs  = Programs((self.radiru, self.radiko, self.jcba, self.misc))
                log('class updated.')
            # 現在時刻が更新予定時刻を過ぎていたら
            if now > self.nextaired:
                # 番組データを取得
                self.nextaired, new_hash = self.programs.setup(renew=True)
                # 放送局に設定変更があると番組データが取得できないので
                if new_hash is None:
                    # クラスを更新して
                    self.update_classes()
                    # 改めて番組データを取得
                    self.nextaired, new_hash = self.programs.setup(renew=True)
                #　番組データが更新されたら
                if new_hash != self.program_hash:
                    self.program_hash = new_hash
                    # ダウンロードする番組を抽出
                    self.programs.match()
                    # 画面更新
                    refresh = True
                    log('program updated. nextaired:{t}'.format(t=self.nextaired))
            # ダウンロードする番組が検出されたら
            if self.programs.matched_programs:
                # ダウンロードを予約
                self.programs.download()
            # 設定更新が検出されたら
            if monitor.settings_changed:
                new_hash = self.hash_settings()
                if new_hash != self.settings_hash:
                    self.settings_hash = new_hash
                    # 画面更新
                    refresh = True
                    log('settings changed.')
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
