# -*- coding: utf-8 -*-


from SimpleHTTPServer import SimpleHTTPRequestHandler
from BaseHTTPServer import HTTPServer

import random
import urllib, urllib2
import urlparse

if __name__  == '__main__':
    # デバッグ用
    class Const:
        @staticmethod
        def SET(attr, value):
            return
        @staticmethod
        def GET(attr):
            if attr == 'apikey': return httpd.apikey
            if attr == 'port': return '8088'
    def log(message):
        print(message)
else:
    from ..const import Const
    from ..common import *


class LocalProxy(HTTPServer):

    # 文字セット
    CHARSET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    # キーの長さ
    LENGTH = 8

    def __init__(self):
        # ポート番号
        port = Const.GET('port')
        # APIキー
        self.apikey = ''.join([LocalProxy.CHARSET[random.randrange(len(LocalProxy.CHARSET))] for i in range(LocalProxy.LENGTH)])
        # APIキーを保存
        Const.SET('apikey', self.apikey)
        # HTTPServerを初期化
        HTTPServer.__init__(self, ('', int(port)), LocalProxyHandler)

    @staticmethod
    def abort():
        # ポート番号
        port = Const.GET('port')
        # APIキー
        apikey = Const.GET('apikey')
        # URLを生成
        exit_url = 'http://127.0.0.1:%s/abort;%s' % (port, apikey)
        # リクエスト
        res = urllib.urlopen(exit_url)
        data = res.read()
        res.close()
        return data

    @staticmethod
    def proxy(url='', headers={}):
        # ポート番号
        port = Const.GET('port')
        # APIキー
        apikey = Const.GET('apikey')
        # URLを生成
        params = {'_': url}
        params.update(headers)
        proxy_url = 'http://127.0.0.1:%s/proxy;%s?%s' % (port, apikey, urllib.urlencode(params))
        return proxy_url

    @staticmethod
    def parse(proxy_url):
        # ソースURLとリクエストヘッダの既定値
        url = proxy_url
        headers = {}
        # プロキシURLを展開
        parsed = urlparse.urlparse(proxy_url)
        # プロキシURLのパスとAPIキーが一致したらソースURLとリクエストヘッダを抽出する
        if parsed.path == '/proxy' and parsed.params == Const.GET('apikey'):
            for key, val in urlparse.parse_qs(parsed.query, keep_blank_values=True).items():
                if key == '_':
                    url = val[0]
                else:
                    headers[key] = val[0]
        return url, headers


class LocalProxyHandler(SimpleHTTPRequestHandler):

    def do_HEAD(self):
        self.body = False
        self.do_request()

    def do_GET(self):
        self.body = True
        self.do_request()

    def log_message(self, format, *args):
        # デフォルトのログ出力を抑制する
        # ('GET /abort;pBVVfZdW HTTP/1.1', '200', '-')
        return

    def do_respond(self, code, message):
        # レスポンスヘッダ
        self.send_response(code)
        self.end_headers()
        # レスポンスボディ
        if self.body:
            self.wfile.write('%d %s' % (code, message))

    def do_request(self):
        try:
            # HTTPリクエストをパースする
            # HTTPリクエスト：GET /proxy;pBVVfZdW?x-radiko-authtoken=PYRk2tStPElKwPIQkPjJ4A&_=https%3A%2F%2Ff-radiko.smartstream.ne.jp%2FTBS%2F_definst_%2Fsimul-stream.stream%2Fplaylist.m3u HTTP/1.1"
            # パース結果：ParseResult(scheme='', netloc='', path='/proxy', params='pBVVfZdW', query='x-radiko-authtoken=PYRk2tStPElKwPIQkPjJ4A&_=https%3A%2F%2Ff-radiko.smartstream.ne.jp%2FTBS%2F_definst_%2Fsimul-stream.stream%2Fplaylist.m3u', fragment='')
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
                        if self.body:
                            req = urllib2.Request(url, headers=headers)
                            self.copyfile(urllib2.urlopen(req), self.wfile)
                            # ログ
                            log('forwarded to: %s' % url)
                    else:
                        self.do_respond(404, 'Not Found')
                        log('not found: %s' % self.path)
                elif parsed.path == '/abort':
                    # レスポンス
                    self.do_respond(200, 'OK')
                    # APIキーを削除
                    self.server.apikey = ''
                    # ログ
                    log('aborted')
                else:
                    self.do_respond(404, 'Not Found')
                    log('not found: %s' % self.path)
            else:
                self.do_respond(403, 'Forbidden')
                log('forbidden: %s' % self.path)
        except:
            self.do_respond(500, 'Internal Server Error')
            log('internal server error: %s' % self.path)


if __name__  == '__main__':
    # ローカルプロキシ
    httpd = LocalProxy()
    print 'apikey: %s' % httpd.apikey
    while httpd.apikey:
        httpd.handle_request()
