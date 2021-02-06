# -*- coding: utf-8 -*-

from resources.lib.service.service import Service
from resources.lib.service.localproxy import LocalProxy

# HTTP接続におけるタイムアウト(秒)
import socket
socket.setdefaulttimeout(60)


if __name__  == '__main__':
    # ローカルプロキシを初期化（APIキーを生成）
    httpd = LocalProxy()
    # 別スレッドでサービスを起動（APIキーを使ってURLを生成）
    import threading
    thread = threading.Thread(target=Service().monitor)
    thread.start()
    # ローカルプロキシを起動
    while httpd.apikey:
        httpd.handle_request()
