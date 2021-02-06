# -*- coding: utf-8 -*-

from SimpleHTTPServer import SimpleHTTPRequestHandler
from BaseHTTPServer import HTTPServer

import random
import urllib, urllib2
import urlparse
import socket

if __name__  == '__main__':
    # デバッグ用
    class Const:
        PROXYSETTINGS_FILE = ''
        @staticmethod
        def GET(attr): return
    def read_json(filepath):
        return
    def write_json(filepath, data):
        return
    def log(message):
        print(message)
else:
    from ..const import Const
    from ..common import *


class LocalProxy(HTTPServer):

    # デフォルトポート番号
    DEFAULT_PORT = '8088'
    # デフォルトAPIキー
    DEFAULT_APIKEY = '12345678'
    # 文字セット
    CHARSET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    # キーの長さ
    LENGTH = 8

    def __init__(self):
        # ポート番号
        port = Const.GET('port') or LocalProxy.DEFAULT_PORT
        # APIキー
        if __name__  == '__main__':
            apikey  = LocalProxy.DEFAULT_APIKEY
        else:
            apikey  = ''.join([LocalProxy.CHARSET[random.randrange(len(LocalProxy.CHARSET))] for i in range(LocalProxy.LENGTH)])
        # プロキシ設定を書き込む
        write_json(Const.PROXYSETTINGS_FILE, {'port':port, 'apikey':apikey})
        # インスタンスにAPIキーを設定
        self.apikey = apikey
        # 起動フラグを設定
        self.running = True
        # HTTPServerを初期化
        HTTPServer.__init__(self, ('', int(port)), LocalProxyHandler)

    @staticmethod
    def settings():
        # プロキシ設定を読み込む
        settings = read_json(Const.PROXYSETTINGS_FILE) or {'port':LocalProxy.DEFAULT_PORT, 'apikey':LocalProxy.DEFAULT_APIKEY}
        return settings['port'], settings['apikey']

    @staticmethod
    def available():
        # プロキシ設定を読み込む
        port, apikey = LocalProxy.settings()
        # ポートを確認する
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', int(port)))
        sock.close()
        if result > 0:
            return True
        else:
            # URLを生成
            hello_url = 'http://127.0.0.1:%s/hello;%s' % (port, apikey)
            # リクエスト
            res = urllib.urlopen(hello_url)
            data = res.read()
            res.close()
            if data == '200 OK':
                return True
            else:
                notify('Port %s is busy' % port)
                return false

    @staticmethod
    def abort():
        # プロキシ設定を読み込む
        port, apikey = LocalProxy.settings()
        # URLを生成
        abort_url = 'http://127.0.0.1:%s/abort;%s' % (port, apikey)
        # リクエスト
        res = urllib.urlopen(abort_url)
        data = res.read()
        res.close()
        return data

    @staticmethod
    def proxy(url='', headers={}):
        # プロキシ設定を読み込む
        port, apikey = LocalProxy.settings()
        # URLを生成
        params = {'_': url}
        params.update(headers)
        proxy_url = 'http://127.0.0.1:%s/proxy;%s?%s' % (port, apikey, urllib.urlencode(params))
        return proxy_url

    @staticmethod
    def parse(proxy_url):
        # プロキシ設定を読み込む
        port, apikey = LocalProxy.settings()
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
                    self.server.running = False
                elif parsed.path == '/hello':
                    # レスポンス
                    self.do_respond(200, 'OK')
                else:
                    self.do_respond(404, 'Not Found')
            else:
                self.do_respond(403, 'Forbidden')
        except Exception as e:
            print e
            self.do_respond(500, 'Internal Server Error')


if __name__  == '__main__':
    # ローカルプロキシ
    httpd = LocalProxy()
    # リクエストを処理する
    while httpd.running:
        httpd.handle_request()
