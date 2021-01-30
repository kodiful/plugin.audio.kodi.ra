# -*- coding: utf-8 -*-

from ..const import Const
from ..common import *

from SimpleHTTPServer import SimpleHTTPRequestHandler
from BaseHTTPServer import HTTPServer

import random
import urllib2
import urlparse


class APIKey:

    # 文字セット
    CHRSET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    # キーの長さ
    LENGTH = 8

    def create(self):
        return ''.join([self.CHRSET[random.randrange(len(self.CHRSET))] for i in range(self.LENGTH)])


class LocalProxy(HTTPServer):

    def __init__(self):
        # APIキー
        self.apikey = Const.GET('apikey')
        # ポート番号
        port = Const.GET('port')
        # HTTPServerを初期化
        HTTPServer.__init__(self, ('', int(port)), LocalProxyHandler)


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
            if self.path[1:1+APIKey.LENGTH] == self.server.apikey:
                # 引数を分解
                args = urlparse.parse_qs(self.path[3+APIKey.LENGTH:], keep_blank_values=True)
                url = ''
                headers = {}
                for key in args.keys():
                    if key == '_':
                        url = args[key][0]
                    else:
                        headers[key] = args[key][0]
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
