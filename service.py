# -*- coding: utf-8 -*-

rom resources.lib.const import Const
from resources.lib.common import *

from resources.lib.service.service import Service
from resources.lib.service.localproxy import LocalProxy

import threading

# HTTP接続におけるタイムアウト(秒)
import socket
socket.setdefaulttimeout(60)


if __name__  == '__main__':
    # ローカルプロキシを初期化（APIキーを設定）
    httpd = LocalProxy()
    # サービスを初期化（APIキーを用いてURLを設定／インストール直後でAPIキーがない場合も設定ダイアログを作成）
    service = Service()
    # APIキーが設定されていればローカルプロキシを起動
    if httpd.apikey:
        # 別スレッドでサービスを起動
        threading.Thread(target=service.monitor).start()
        # ローカルプロキシを起動
        while httpd.apikey:
            httpd.handle_request()
    else:
        # インストール直後などAPIキーが設定できなかったときはKodiの再起動を促す
        notify('Restart Kodi to enable local proxy')
