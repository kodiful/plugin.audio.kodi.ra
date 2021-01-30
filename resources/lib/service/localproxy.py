# -*- coding: utf-8 -*-

try:
    from ..const import Const
    from ..common import *
except:
    # デバッグ用
    #
    # http://127.0.0.1:8088/12345678/?_=http://kodiful.com
    #
    class Const:
        @staticmethod
        def GET(attr):
            if attr == 'apikey': return '12345678'
            if attr == 'port': return '8088'


from SimpleHTTPServer import SimpleHTTPRequestHandler
from BaseHTTPServer import HTTPServer

import random
import urllib, urllib2
import urlparse


class APIKey:

    # 文字セット
    CHRSET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    # キーの長さ
    LENGTH = 8

    def generate(self):
        return ''.join([self.CHRSET[random.randrange(len(self.CHRSET))] for i in range(self.LENGTH)])


class LocalProxy(HTTPServer):

    def __init__(self):
        # ポート番号
        port = Const.GET('port')
        # HTTPServerを初期化
        HTTPServer.__init__(self, ('', int(port)), LocalProxyHandler)

    @staticmethod
    def proxy(url, headers):
        # ポート番号
        port = Const.GET('port')
        # APIキー
        apikey = Const.GET('apikey')
        # パスとクエリに設定する
        params = {'_': url}
        params.update(headers)
        url = 'http://127.0.0.1:%s/%s/?%s' % (port, apikey, urllib.urlencode(params))
        return url

    @staticmethod
    def parse(proxy_url):
        # ソースURLとリクエストヘッダの既定値
        url = proxy_url
        headers = {}
        # プロキシURLを展開
        parsed = urlparse.urlparse(proxy_url)
        # プロキシURLのパスとAPIキーが一致したらソースURLとリクエストヘッダを抽出する
        if parsed.path.strip('/') == Const.GET('apikey'):
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

    def do_response(self, code, message):
        # レスポンスヘッダ
        self.send_response(code)
        self.end_headers()
        # レスポンスボディ
        if self.body:
            self.wfile.write('%d %s' % (code, message))

    def do_request(self):
        try:
            # HTTPリクエスト
            #
            # GET /pBVVfZdW/?x-radiko-authtoken=PYRk2tStPElKwPIQkPjJ4A&_=https%3A%2F%2Ff-radiko.smartstream.ne.jp%2FTBS%2F_definst_%2Fsimul-stream.stream%2Fplaylist.m3u HTTP/1.1"
            #
            parsed = urlparse.urlparse(self.path)
            #
            # ParseResult(scheme='', netloc='', path='/pBVVfZdW/', params='', query='x-radiko-authtoken=PYRk2tStPElKwPIQkPjJ4A&_=https%3A%2F%2Ff-radiko.smartstream.ne.jp%2FTBS%2F_definst_%2Fsimul-stream.stream%2Fplaylist.m3u', fragment='')
            #
            # APIキーをチェック
            if parsed.path.strip('/') == Const.GET('apikey'):
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
                else:
                    self.do_response(404, 'Not Found')
            else:
                self.do_response(403, 'Forbidden')
        except:
            self.do_response(500, 'Internal Server Error')


if __name__  == '__main__': LocalProxy().serve_forever()
