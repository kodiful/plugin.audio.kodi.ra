# -*- coding: utf-8 -*-

from resources.lib.const import Const
from resources.lib.common import log

import random
import socket
import urllib

from http.server import ThreadingHTTPServer
from http.server import SimpleHTTPRequestHandler


class LocalProxy(ThreadingHTTPServer):

    # 文字セット
    CHARSET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    # キーの長さ
    LENGTH = 8

    def __init__(self):
        # ポート番号
        self.activeport = Const.GET('port')
        # ポート番号が取得できたらHTTPサーバを準備する
        if self.activeport:
            # ポートが利用可能か確認する
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = s.connect_ex(('127.0.0.1', int(self.activeport)))
            s.close()
            if result > 0:
                # アクティブなポート番号として保存
                Const.SET('activeport', self.activeport)
                # APIキー
                self.apikey = ''.join([LocalProxy.CHARSET[random.randrange(len(LocalProxy.CHARSET))] for i in range(LocalProxy.LENGTH)])
                # APIキーを保存
                Const.SET('apikey', self.apikey)
                # ログ
                log('apikey initialized: %s' % self.apikey)
                # HTTPサーバを初期化
                super().__init__(('', int(self.activeport)), LocalProxyHandler)
            else:
                # ポート番号が利用できない場合はローカルプロキシの設定変更を促す
                self.apikey = None
                # 通知メッセージ
                self.message = 'Local proxy port %s is busy' % self.activeport
        else:
            # ポート番号が取得できないインストール直後はKodiの再起動を促す
            self.apikey = None
            # 通知メッセージ
            self.message = 'Restart Kodi to enable local proxy'

    @staticmethod
    def abort():
        # ポート番号
        activeport = Const.GET('activeport')
        # APIキー
        apikey = Const.GET('apikey')
        # URLを生成
        abort_url = 'http://127.0.0.1:%s/abort;%s' % (activeport, apikey)
        # リクエスト
        res = urllib.request.urlopen(abort_url)
        data = res.read()
        res.close()
        return data

    @staticmethod
    def proxy(url='', headers={}):
        # ポート番号
        activeport = Const.GET('activeport')
        # APIキー
        apikey = Const.GET('apikey')
        # URLを生成
        params = {'_': url}
        params.update(headers)
        proxy_url = 'http://127.0.0.1:%s/proxy;%s?%s' % (activeport, apikey, urllib.parse.urlencode(params))
        return proxy_url

    @staticmethod
    def parse(proxy_url):
        # APIキー
        apikey = Const.GET('apikey')
        # ソースURLとリクエストヘッダの既定値
        url = proxy_url
        headers = {}
        # プロキシURLを展開
        parsed = urllib.parse.urlparse(proxy_url)
        # URLのパスとAPIキーが一致したらソースURLとリクエストヘッダを抽出する
        if parsed.path == '/proxy' and parsed.params == apikey:
            for key, val in urllib.parse.parse_qs(parsed.query, keep_blank_values=True).items():
                if key == '_':
                    url = val[0]
                else:
                    headers[key] = val[0]
        return url, headers


class LocalProxyHandler(SimpleHTTPRequestHandler):

    def do_HEAD(self):
        self.do_request()

    def do_GET(self):
        self.do_request()

    def log_message(self, format, *args):
        # デフォルトのログ出力を抑制する
        # format: '"%s" %s %s'
        # args: ('GET /abort;pBVVfZdW HTTP/1.1', '200', '-')
        return

    def do_respond(self, code, message):
        # レスポンスヘッダ
        self.send_response(code)
        self.end_headers()
        # レスポンスボディ
        if self.command == 'GET':
            # HTTPステータスを返す
            self.wfile.write('%d %s' % (code, message))
            # ログ
            log('%s: %s' % (message, self.path))

    def do_request(self):
        try:
            # HTTPリクエストをパースする
            # リクエスト： GET /proxy;pBVVfZdW?x-radiko-authtoken=PYRk2tStPElKwPIQkPjJ4A&_=https%3A%2F%2Ff-radiko.smartstream.ne.jp%2FTBS%2F_definst_%2Fsimul-stream.stream%2Fplaylist.m3u HTTP/1.1"
            # パース結果： ParseResult(scheme='', netloc='', path='/proxy', params='pBVVfZdW', query='x-radiko-authtoken=PYRk2tStPElKwPIQkPjJ4A&_=https%3A%2F%2Ff-radiko.smartstream.ne.jp%2FTBS%2F_definst_%2Fsimul-stream.stream%2Fplaylist.m3u', fragment='')
            parsed = urllib.parse.urlparse(self.path)
            # APIキーをチェック
            if parsed.params == self.server.apikey:
                # パスに応じて処理
                if parsed.path == '/proxy':
                    # クエリを展開
                    url, headers = LocalProxy.parse(self.path)
                    # レスポンス
                    if url:
                        # レスポンスヘッダ（OK）
                        self.send_response(200)
                        self.end_headers()
                        # レスポンスボディ
                        if self.command == 'GET':
                            req = urllib.request.Request(url, headers=headers)
                            data = urllib.request.urlopen(req).read()
                            self.wfile.write(data)
                            # ログ
                            log('forwarded to: %s' % url)
                    else:
                        self.do_respond(404, 'Not Found')
                elif parsed.path == '/abort':
                    # レスポンス
                    self.do_respond(200, 'OK')
                    # APIキーを削除
                    self.server.apikey = ''
                elif parsed.path == '/hello':
                    # レスポンス
                    self.do_respond(200, 'OK')
                else:
                    self.do_respond(404, 'Not Found')
            else:
                self.do_respond(403, 'Forbidden')
        except Exception:
            self.do_respond(500, 'Internal Server Error')
