# -*- coding: utf-8 -*-

from resources.lib.const import Const
from resources.lib.common import *
from resources.lib.compatibility import Compatibility

import os
import platform
import threading
import xbmc, xbmcgui

from hashlib import md5

from resources.lib.cp.radiko import Radiko, Authenticate
from resources.lib.cp.radiru import Radiru
from resources.lib.cp.jcba   import Jcba
from resources.lib.cp.misc   import Misc

from resources.lib.programs  import Programs
from resources.lib.downloads import Downloads

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
        # 互換性チェック
        if Const.GET('compatibility') == 'true':
            # 古い形式のファイルの変換
            Compatibility().converter()
        # ディレクトリをチェック
        if not os.path.isdir(Const.CACHE_PATH): os.makedirs(Const.CACHE_PATH)
        if not os.path.isdir(Const.MEDIA_PATH): os.makedirs(Const.MEDIA_PATH)
        if not os.path.isdir(Const.DATA_PATH):  os.makedirs(Const.DATA_PATH)
        # いろいろ初期化
        self.lastupdt = ''
        self.nextupdt = ''
        self.lastauth = ''
        self.nextauth = ''
        self.programs_hash = ''
        self.settings_hash = self.hash_settings()
        # radiko認証
        self.nextauth = self.authenticate()
        # クラスを初期化
        self.update_classes(renew=True)
        # 設定ダイアログを作成
        self.setup_settings()

    def authenticate(self):
        # radiko認証
        auth = Authenticate()
        if auth.response['authed'] == 0:
            # 認証失敗を通知
            notify('radiko authentication failed', error=True)
        else:
            # 時刻を記録
            self.lastauth = timestamp()
        # 認証情報をファイルに書き込む
        self.auth = auth.response
        write_json(Const.AUTH_FILE, self.auth)
        # ログ
        log('radiko authentication status:{status}'.format(status=auth.response['authed']))
        # 次の更新時刻を返す
        return timestamp(Const.AUTH_INTERVAL)

    def update_classes(self, renew=False):
        self.radiru = Radiru(renew)
        self.radiko = Radiko(area=self.auth['area_id'], token=self.auth['auth_token'], renew=renew)
        self.jcba = Jcba(renew)
        self.misc = Misc(renew)
        self.programs = Programs((self.radiru, self.radiko, self.jcba, self.misc))
        return self.programs.setup(renew)

    def setup_settings(self):
        # 放送局リスト
        s = [Const.STR(30520)]
        stations = Programs((self.radiru,self.radiko)).stations
        for station in stations:
            s.append(station['name'])
        # テンプレート読み込み
        template = read_file(Const.TEMPLATE_FILE)
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
        # ログ
        log('settings initialized.')

    def hash_settings(self):
        settings = read_file(Const.USERSETTINGS_FILE)
        return md5(settings).hexdigest() if settings else ''

    def monitor(self, refresh=False):
        # 開始
        log('enter monitor.')
        # 監視開始を通知
        notify('Starting service')
        # 初期化
        now = ''
        downloader = Downloads(cleanup=True)
        # 監視処理を実行
        monitor = Monitor()
        while not monitor.abortRequested():
            # 初回は待機しない
            if now == '':
                pass
            # Const.CHECK_INTERVALの間待機
            elif monitor.waitForAbort(Const.CHECK_INTERVAL):
                break
            # 現在時刻
            now = timestamp()
            # リセットが検出されたら（設定ダイアログ削除が検出されたら）
            if not os.path.isfile(Const.SETTINGS_FILE):
                # クラスを更新
                self.nextupdt, self.programs_hash = self.update_classes()
                # 設定ダイアログを生成
                self.setup_settings()
                # ユーザ設定のハッシュ
                self.settings_hash = self.hash_settings()
                # 画面更新
                refresh = True
                log('settings initialized.')
            # 現在時刻がRadiko認証更新時刻を過ぎていたら
            if now > self.nextauth:
                # radiko認証
                self.nextauth = self.authenticate()
                # クラスを更新
                self.radiko = Radiko(area=self.auth['area_id'], token=self.auth['auth_token'], renew=True)
                self.programs  = Programs((self.radiru, self.radiko, self.jcba, self.misc))
            # 現在時刻が更新予定時刻を過ぎていたら
            if now > self.nextupdt:
                # 番組データを取得
                self.nextupdt, new_hash = self.programs.setup()
                #　番組データが更新されたら
                if new_hash != self.programs_hash:
                    self.lastupdt = now
                    self.programs_hash = new_hash
                    # 番組情報を記録
                    if Const.GET('record'): self.programs.record()
                    # ダウンロードする番組を抽出
                    downloader.pending = self.programs.match(downloader.pending)
                    # 画面更新
                    refresh = True
            # キューファイルが検出されたら
            if os.path.isfile(Const.QUEUE_FILE):
                queue = read_json(Const.QUEUE_FILE)
                for p in queue:
                    downloader.pending.append({'program':p, 'keyword':{'key':''}})
                os.remove(Const.QUEUE_FILE)
            # ダウンロードする番組が検出されたら
            if downloader.pending:
                # ダウンロードキューを処理
                downloader.filter()
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
            # スレッドリストのメンテナンス
            downloader.thread = filter(lambda t:t.is_alive(), downloader.thread)
            downloader.process = filter(lambda p:p.returncode is None, downloader.process)
            # ステータスを出力
            write_json(Const.STATUS_FILE, {
                'now': now,
                'auth': {
                    'last': self.lastauth,
                    'next': self.nextauth
                },
                'updt': {
                    'last': self.lastupdt,
                    'next': self.nextupdt
                },
                'hash': {
                    'programs': self.programs_hash,
                    'settings': self.settings_hash
                },
                'downloads': {
                    'pending': len(downloader.pending),
                    'threads': len(downloader.thread),
                    'ongoing': len(downloader.process)
                }
            })
        # 終了
        downloader.abort()
        log('exit monitor.')


if __name__  == '__main__': Service().monitor()
