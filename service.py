# -*- coding: utf-8 -*-

from resources.lib.keywords import(Keywords)
from default import(start)

from resources.lib.common import(__addon__)

# 番組保存設定がある場合はバックグラウンドで起動する
if __addon__.getSetting('download') == 'true' and len(Keywords().search) > 0: start(False)
