# -*- coding: utf-8 -*-

from resources.lib.const import Const
from resources.lib.common import *
from resources.lib.keywords import Keywords
from default import start

# HTTP接続におけるタイムアウト(秒)
import socket
socket.setdefaulttimeout(60)

# 番組保存設定がある場合はバックグラウンドで起動する
if Const.GET('download') == 'true' and len(Keywords().keywords) > 0:
    # 通知
    notify('Starting service', time=3000)
    # 起動
    start(background=True)
