# -*- coding: utf-8 -*-

from .const import Const
from .common import *
from .holiday import Holiday
from .rss import RSS

import datetime, time
import os
import subprocess
import sys
import glob
import shutil
import json
import re
import threading
import xbmc, xbmcgui, xbmcplugin, xbmcaddon


class Params:
    # ログファイル
    LOG_FILE = os.path.join(Const.DOWNLOAD_PATH, 'download.log')


class Logger():

    def __init__(self, logfile):
        self.handle = open(logfile, 'a')

    def write(self, message=''):
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.handle.write('%s\t%s\n' % (now, message))
        self.handle.flush()

    def flush(self):
        self.handle.flush()


class Downloads:

    def __init__(self):
        return

    def status(self, id, ft):
        # 番組ID
        gtvid = '%s_%s' % (id, ft);
        # ファイルパス
        json_file  = os.path.join(Const.DOWNLOAD_PATH, '%s.json' % gtvid)
        tmp_file = os.path.join(Const.DOWNLOAD_PATH, '.%s.mp3' % gtvid)
        mp3_file = os.path.join(Const.DOWNLOAD_PATH, '%s.mp3' % gtvid)
        # 既存の番組情報ファイルの有無をチェック
        status = 0
        if os.path.isfile(json_file): status += 1
        if os.path.isfile(tmp_file): status += 2
        if os.path.isfile(mp3_file): status += 4
        return status

    def add(self, id, name, ft, to, title, description, source, delay, key=''):
        # 既存の番組情報ファイルの有無をチェック
        status = self.status(id, ft)
        if status & 4: return 'Already downloaded'
        if status & 2: return 'Now downloading'
        if status & 1: return 'Already scheduled'
        # 番組ID
        gtvid = '%s_%s' % (id, ft);
        # ファイルパス
        json_file  = os.path.join(Const.DOWNLOAD_PATH, '%s.json' % gtvid)
        tmp_file = os.path.join(Const.DOWNLOAD_PATH, '.%s.mp3' % gtvid)
        mp3_file = os.path.join(Const.DOWNLOAD_PATH, '%s.mp3' % gtvid)
        # 現在時刻
        now = datetime.datetime.now()
        # 開始時間
        start = strptime(ft, '%Y%m%d%H%M%S')
        startdate = start.strftime('%Y-%m-%d %H:%M:%S')
        # 終了時間
        end = strptime(to, '%Y%m%d%H%M%S')
        # ラグ調整
        delay = datetime.timedelta(seconds=int(delay))
        start = start + delay
        end = end + delay
        # 録音開始の設定
        if start > now:
            # まだ始まっていない場合は開始を待つ
            wait = start - now
            wait = wait.seconds
        else:
            # すでに始まっている場合
            if end > now:
                # まだ終わっていない場合はすぐ開始する
                start = now
                wait = 0
            else:
                # すでに終わっている場合はこのまま終了する
                return 'Program is over'
        # 録音時間
        duration = end - start
        if duration.seconds > 0:
            if wait == 0:
                # すぐ開始する場合
                duration = duration.seconds + Const.MARGIN_INTERVAL
            else:
                if wait > Const.MARGIN_INTERVAL:
                    duration = duration.seconds + Const.MARGIN_INTERVAL + Const.MARGIN_INTERVAL
                    wait = wait - Const.MARGIN_INTERVAL
                else:
                    duration = duration.seconds + wait + Const.MARGIN_INTERVAL
                    wait = 0
        else:
            # durationが異常値
            return 'Invalid duration'
        # ビットレート
        bitrate = Const.GET('bitrate')
        if bitrate == 'auto':
            if duration <= 3600:
                bitrate = '192k'
            elif duration <= 4320:
                bitrate = '160k'
            elif duration <= 5400:
                bitrate = '128k'
            elif duration <= 7200:
                bitrate = '96k'
            else:
                bitrate = '64k'
        # ソース
        conn = []
        match = re.findall(r'conn=[^ ]+', source)
        for m in match:
            conn.append(re.sub(r'conn=', '', m))
        if len(conn) > 0:
            rtmp_conn = '-rtmp_conn "%s"' % ' '.join(conn)
        else:
            rtmp_conn = ''
        match = re.match(r'(?:rtmp|rtmps|rtmpe|rtmpt)://[^ ]+', source)
        if match:
            source = match.group()
        # 番組情報
        data = {
            'gtvid': gtvid,
            'id': id,
            'name': name,
            'ft': ft,
            'to': to,
            'title': title,
            'description': description,
            'source': source,
            'key': '',
            'duration': duration
        }
        # 番組情報を保存
        write_json(json_file, data)
        # 別スレッドでダウンロードを実行
        data = {
            'ffmpeg': Const.GET('ffmpeg'),
            'wait': wait,
            'start': start,
            'duration': duration,
            'rtmp_conn': rtmp_conn,
            'source': source,
            'bitrate': bitrate,
            'title': title,
            'artist': name,
            'copyright': name,
            'publisher': name,
            'date': start.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'tit1': key,
            'tit3': description,
            'mp3_file': mp3_file,
            'tmp_file': tmp_file
        }
        threading.Thread(target=self.__thread, args=[data]).start()

    def __thread(self, data):
        # コマンドライン
        command = ('{ffmpeg} -y -v warning -t {duration} {rtmp_conn} -i "{source}" -acodec libmp3lame -b:a {bitrate} '
            + '-metadata title="{title}" '
            + '-metadata artist="{artist}" '
            + '-metadata copyright="{copyright}" '
            + '-metadata publisher="{publisher}" '
            + '-metadata date="{date}" '
            + '-metadata TIT1="{tit1}" '
            + '-metadata TIT3="{tit3}" '
            + '"{tmp_file}"').format(
                ffmpeg=data['ffmpeg'],
                duration=data['duration'],
                rtmp_conn=data['rtmp_conn'],
                source=data['source'],
                bitrate=data['bitrate'],
                title=data['title'],
                artist=data['artist'],
                copyright=data['copyright'],
                publisher=data['publisher'],
                date=data['start'].strftime('%Y-%m-%dT%H:%M:%SZ'),
                tit1=data['tit1'],
                tit3=data['tit3'],
                tmp_file=data['tmp_file'])
        # 開始待機
        if data['wait'] > 0: time.sleep(data['wait'])
        # 開始通知
        notify('Download started')
        # ログ
        logger = Logger(Params.LOG_FILE)
        logger.write('downloading \'%s\' to \'%s\' ...' % (data['title'], data['mp3_file']))
        # ダウンロード開始
        p = subprocess.Popen(command, stderr=logger.handle, stdout=logger.handle, shell=True)
        # ダウンロード終了を待つ
        p.wait()
        # ダウンロード結果に応じて後処理
        if p.returncode:
            # 失敗したときはjsonファイル、一時ファイルを削除
            os.remove(data['json_file'])
            os.remove(data['tmp_file'])
        else:
            # 一時ファイルをリネーム
            os.rename(data['tmp_file'], data['mp3_file'])
            # rssファイル生成
            RSS().create()
        # ダウンロード終了
        logger.write('done (returncode=%d).' % p.returncode)
        # 完了通知
        if p.returncode:
            notify('Download failed (returncode=%d)' % p.returncode, error=True)
        else:
            notify('Downloaded successfully')

    def deleteall(self):
        # ファイル削除
        for file in glob.glob(os.path.join(Const.DOWNLOAD_PATH, '*.*')):
            if os.path.isfile(file): os.remove(file)
        # rssファイル生成
        RSS().create()
        # 再表示
        xbmc.executebuiltin('Container.Update(%s,replace)' % (sys.argv[0]))

    def delete(self, gtvid):
        # ファイル削除
        for file in glob.glob(os.path.join(Const.DOWNLOAD_PATH, '%s.*' % (gtvid))):
            if os.path.isfile(file): os.remove(file)
        # rssファイル生成
        RSS().create()
        # 再表示
        xbmc.executebuiltin('Container.Update(%s,replace)' % (sys.argv[0]))

    def show(self, key=''):
        plist = []
        for file in glob.glob(os.path.join(Const.DOWNLOAD_PATH, '*.json')):
            json_file = os.path.join(Const.DOWNLOAD_PATH, file)
            mp3_file = os.path.join(Const.DOWNLOAD_PATH, file.replace('.json','.mp3'))
            if os.path.isfile(mp3_file):
                plist.append(read_json(json_file))
            else:
                log('lost file=', mp3_file)
        # 日付フォーマット
        h = Holiday()
        # 時間の逆順にソートして表示
        for p in sorted(plist, key=lambda item: item['ft'], reverse=True):
            try:
                p['key']
            except:
                p['key'] = ''
            if key == '' or key==p['key']:
                # title
                title = '%s [COLOR khaki]%s[/COLOR] [COLOR lightgreen](%s)[/COLOR]' % (h.format(p['ft']),p['title'], p['name'])
                # logo
                id = p['gtvid'].split('_')
                logopath = os.path.join(Const.MEDIA_PATH, 'logo_%s_%s.png' % (id[0],id[1]))
                if not os.path.isfile(logopath): logopath = 'DefaultFile.png'
                # listitemを追加
                li = xbmcgui.ListItem(title, iconImage=logopath, thumbnailImage=logopath)
                #li.setInfo(type='music', infoLabels={'title':p['title'],'duration':p['duration'],'artist':p['bc'],'comment':p['description']})
                comment = p['description']
                comment = re.sub(r'&lt;.*?&gt;','\n', comment)
                comment = re.sub(r'\n{2,}', '\n', comment)
                comment = re.sub(r'^\n+', '', comment)
                comment = re.sub(r'\n+$', '', comment)
                li.setInfo(type='music', infoLabels={'title':p['title'],'duration':p['duration'],'artist':p['name'],'comment':comment})
                li.setProperty('IsPlayable', 'true')
                # context menu
                li.addContextMenuItems([(Const.STR(30314), 'RunPlugin(%s?action=deleteDownload&id=%s)' % (sys.argv[0],p['gtvid']))], replaceItems=True)
                # add directory item
                # file
                mp3_file = os.path.join(Const.DOWNLOAD_PATH, p['gtvid'] + '.mp3')
                xbmcplugin.addDirectoryItem(int(sys.argv[1]), mp3_file, li, isFolder=False)
        xbmcplugin.endOfDirectory(int(sys.argv[1]), succeeded=True)
