# -*- coding: utf-8 -*-

from resources.lib.service.service import Service
from resources.lib.service.localproxy import LocalProxy

import threading

# HTTP接続におけるタイムアウト(秒)
import socket
socket.setdefaulttimeout(60)


if __name__  == '__main__':
    # ローカルプロキシを初期化（APIキーを生成）
    httpd = LocalProxy()
    # APIキーが生成されたら
    if httpd.apikey:
        # 別スレッドでサービスを起動（APIキーを使ってURLを生成）
        threading.Thread(target=Service().monitor).start()
        # ローカルプロキシを起動
        while httpd.apikey:
            httpd.handle_request()
