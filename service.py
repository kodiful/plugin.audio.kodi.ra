# -*- coding: utf-8 -*-

from resources.lib.service.service import Service
from resources.lib.service.localproxy import LocalProxy

# HTTP接続におけるタイムアウト(秒)
import socket
socket.setdefaulttimeout(60)


if __name__  == '__main__':

    # サービス
    import threading
    thread = threading.Thread(target=Service().monitor)
    thread.start()

    # ローカルプロキシ
    proxy = LocalProxy()
    proxy.serve_forever()
