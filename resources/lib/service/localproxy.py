# -*- coding: utf-8 -*-

from SimpleHTTPServer import SimpleHTTPRequestHandler
from BaseHTTPServer import HTTPServer

import random
import urllib, urllib2
import urlparse

from ..const import Const
from ..common import *


class LocalProxy(HTTPServer):

    # 文字セット
    CHARSET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    # キーの長さ
    LENGTH = 8

    def __init__(self):
        # ポート番号
        self.activeport = Const.GET('port')
        if self.activeport:
            # アクティブなポート番号として保存
            Const.SET('activeport', self.activeport)
            # APIキー
            self.apikey = ''.join([LocalProxy.CHARSET[random.randrange(len(LocalProxy.CHARSET))] for i in range(LocalProxy.LENGTH)])
            # APIキーを保存
            Const.SET('apikey', self.apikey)
            # ログ
            log('apikey initialized: %s' % self.apikey)
            # HTTPServerを初期化
            HTTPServer.__init__(self, ('', int(self.activeport)), LocalProxyHandler)
        else:
            notify('Restart Kodi to enable local proxy')

    @staticmethod
    def abort():
        # ポート番号
        activeport = Const.GET('activeport')
        # APIキー
        apikey = Const.GET('apikey')
        # URLを生成
        abort_url = 'http://127.0.0.1:%s/abort;%s' % (activeport, apikey)
        # リクエスト
        res = urllib.urlopen(abort_url)
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
        proxy_url = 'http://127.0.0.1:%s/proxy;%s?%s' % (activeport, apikey, urllib.urlencode(params))
        return proxy_url

    @staticmethod
    def parse(proxy_url):
        # APIキー
        apikey = Const.GET('apikey')
        # ソースURLとリクエストヘッダの既定値
        url = proxy_url
        headers = {}
        # プロキシURLを展開
        parsed = urlparse.urlparse(proxy_url)
        # URLのパスとAPIキーが一致したらソースURLとリクエストヘッダを抽出する
        if parsed.path == '/proxy' and parsed.params == apikey:
            for key, val in urlparse.parse_qs(parsed.query, keep_blank_values=True).items():
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
            parsed = urlparse.urlparse(self.path)
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
                            req = urllib2.Request(url, headers=headers)
                            self.copyfile(urllib2.urlopen(req), self.wfile)
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
        except:
            self.do_respond(500, 'Internal Server Error')
