# -*- coding: utf-8 -*-

import resources.lib.common as common
from resources.lib.keywords import(Keywords)
from default import(start)

# 番組保存設定がある場合はバックグラウンドで起動する
if common.addon.getSetting('download') == 'true' and len(Keywords().search) > 0:
    # 通知
    common.notify('Starting service', time=3000)
    # 起動
    start(False)
