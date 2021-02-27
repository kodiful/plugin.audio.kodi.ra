# -*- coding: utf-8 -*-

# HTTP接続のタイムアウト(秒)を設定
import socket
socket.setdefaulttimeout(60)

import sys
import os
import threading

# extディレクトリをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), 'resources', 'ext'))

from resources.lib.common import notify
from resources.lib.service import Service
from resources.lib.localproxy import LocalProxy


if __name__ == '__main__':
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
    elif httpd.message:
        # インストール直後やポート番号が競合している場合などAPIキーが設定できなかったときは通知する
        notify(httpd.message)
