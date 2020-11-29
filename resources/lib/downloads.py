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

    def __init__(self, cleanup=False):
        self.pending = []
        self.thread = []
        self.process = []
        self.alive = True
        # ディレクトリのクリーンアップ
        if cleanup:
            # jsonファイル
            for json_file in glob.glob(os.path.join(Const.DOWNLOAD_PATH, '*.json')):
                mp3_file = re.sub(r'\.json$', '.mp3', json_file)
                # 対応するmp3ファイルがない場合は削除
                if not os.path.isfile(mp3_file): os.remove(json_file)
            # 一時ファイル
            for tmp_file in glob.glob(os.path.join(Const.DOWNLOAD_PATH, '.*.mp3')):
                os.remove(tmp_file)
            # キューファイル
            if os.path.isfile(Const.QUEUE_FILE):
                os.remove(Const.QUEUE_FILE)

    def abort(self):
        self.alive = False
        for p in self.process:
            # 実行中のffmepegを強制終了
            if p.returncode is None: p.kill()

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

    def enqueue(self, id, name, ft, to, title, description, stream, url, delay):
        # 時刻をチェック
        if to < timestamp(): return 'Already over'
        # 既存の番組情報ファイルの有無をチェック
        status = self.status(id, ft)
        if status & 4: return 'Already downloaded'
        if status & 2: return 'Already scheduled and now downloading'
        if status & 1: return 'Already scheduled'
        # 既存のキューをファイルから読み込む
        queue = []
        if os.path.isfile(Const.QUEUE_FILE):
            queue = read_json(Const.QUEUE_FILE)
        # キューに追加
        queue.append({
            'id': id,
            'name': name,
            'ft': ft,
            'to': to,
            'title': title,
            'description': description,
            'stream': stream,
            'url': url,
            'delay': delay
        })
        # キューをファイルにに書き込む
        write_json(Const.QUEUE_FILE, queue)

    def filter(self):
        remaining = []
        now = datetime.datetime.now()
        for m in self.pending:
            p = m['program']
            k = m['keyword']
            # 開始直前であれば保存処理を開始
            start = strptime(p['ft'], '%Y%m%d%H%M%S') - now
            end = strptime(p['to'], '%Y%m%d%H%M%S') - now
            # すでに終了している番組
            if end.days < 0:
                log('download abandoned. id:{id}, start:{start}, title:{title}, keyword:{keyword}'.format(
                    id = p['id'],
                    start = p['ft'],
                    title = p['title'],
                    keyword = k['key']))
                # 次の番組のダウンロード処理へ
                continue
            # すでに開始している番組、開始していないがConst.PREP_INTERVAL以内に開始する番組
            elif start.days < 0 or (start.days == 0 and start.seconds < Const.PREP_INTERVAL):
                # ダウンロード実行
                status = self.start(
                    id=p['id'],
                    name=p['name'],
                    ft=p['ft'],
                    to=p['to'],
                    title=p['title'],
                    description=p['description'],
                    stream=p['stream'],
                    delay=p['delay'],
                    url=p['url'],
                    key=k['key'])
                # 正常終了したらログに書き出す
                if status is None:
                    log('download scheduled. id:{id}, start:{start}, title:{title}, keyword:{keyword}'.format(
                        id = p['id'],
                        start = p['ft'],
                        title = p['title'],
                        keyword = k['key']))
                # 次の番組のダウンロード処理へ
                continue
            # Const.PREP_INTERVAL以降に開始する番組
            else:
                # ダウンロード待ちの番組としてリストに追加
                remaining.append(m)
        self.pending = remaining

    def start(self, id, name, ft, to, title, description, stream, delay, url='', key=''):
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
        match = re.findall(r'conn=[^ ]+', stream)
        for m in match:
            conn.append(re.sub(r'conn=', '', m))
        if len(conn) > 0:
            rtmp_conn = '-rtmp_conn "%s"' % ' '.join(conn)
        else:
            rtmp_conn = ''
        match = re.match(r'(?:rtmp|rtmps|rtmpe|rtmpt)://[^ ]+', stream)
        if match:
            stream = match.group()
        # 番組情報
        data = {
            'gtvid': gtvid,
            'id': id,
            'name': name,
            'ft': ft,
            'to': to,
            'title': title,
            'description': description,
            'stream': stream,
            'url': url,
            'key': key,
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
            'stream': stream,
            'bitrate': bitrate,
            'title': title,
            'artist': name,
            'copyright': name,
            'publisher': name,
            'date': start.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'tit1': key,
            'tit3': description,
            'json_file': json_file,
            'tmp_file': tmp_file,
            'mp3_file': mp3_file
        }
        t = threading.Thread(target=self.__thread, args=[data])
        t.start()
        self.thread.append(t)

    def __thread(self, data):
        # コマンドライン
        command = ('"{ffmpeg}" -y -v warning -t {duration} {rtmp_conn} -i "{stream}" -acodec libmp3lame -b:a {bitrate} '
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
                stream=data['stream'],
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
        t = data['wait']
        while t > 0 and self.alive:
            time.sleep(1)
            t -= 1
        if self.alive:
            # 開始通知
            notify('Download started "{title}"'.format(title=data['title']))
            # ログ書き込み初期化
            logger = Logger(Const.LOG_FILE)
            # ダウンロード開始
            p = subprocess.Popen(command, stderr=logger.handle, stdout=logger.handle, shell=True)
            self.process.append(p)
            # ログ
            logger.write('[{pid}] Download started. title:"{title}" file:"{mp3_file}"'.format(pid=p.pid, title=data['title'], mp3_file=data['mp3_file']))
            # ダウンロード終了を待つ
            p.wait()
            # ダウンロード結果に応じて後処理
            if p.returncode == 0:
                # 一時ファイルをリネーム
                os.rename(data['tmp_file'], data['mp3_file'])
                # rssファイル生成
                RSS().create()
                # 完了通知
                notify('Download completed "{title}"'.format(title=data['title']))
                # ログ
                logger.write('[{pid}] Download completed.'.format(pid=p.pid))
            else:
                # 失敗したときはjsonファイル、一時ファイルを削除
                os.remove(data['json_file'])
                os.remove(data['tmp_file'])
                # 完了通知
                notify('Download failed "{title}"'.format(title=data['title']), error=True)
                # ログ
                logger.write('[{pid}] Download failed. returncode:{returncode}'.format(pid=p.pid, returncode=p.returncode))
        else:
            # 中断した時はjsonファイルを削除
            os.remove(data['json_file'])

    def delete(self, gtvid=None, key=None):
        # ファイル削除
        if gtvid is None and key is None:
            files = glob.glob(os.path.join(Const.DOWNLOAD_PATH, '*.json'))
        elif gtvid is not None:
            files = glob.glob(os.path.join(Const.DOWNLOAD_PATH, '%s.json' % gtvid))
        elif key is not None:
            files = filter(lambda file:read_json(file).get('key','')==key, glob.glob(os.path.join(Const.DOWNLOAD_PATH, '*.json')))
        else:
            files = []
        # ファイル削除
        if len(files) > 0:
            for file in files:
                json_file = file
                tmp_file = '.%s' % file
                mp3_file  = file.replace('.json', '.mp3')
                os.remove(json_file)
                if os.path.isfile(tmp_file): os.remove(tmp_file)
                if os.path.isfile(mp3_file): os.remove(mp3_file)
            # rssファイル生成
            RSS().create()

    def show(self, key=''):
        plist = []
        for json_file in glob.glob(os.path.join(Const.DOWNLOAD_PATH, '*.json')):
            tmp_file = '.%s' % json_file
            mp3_file = json_file.replace('.json', '.mp3')
            if os.path.isfile(mp3_file):
                plist.append(read_json(json_file))
            else:
                log('file lost (or in downloading):{file}'.format(file=mp3_file))
        # 日付フォーマット
        h = Holiday()
        # 時間の逆順にソートして表示
        for p in sorted(plist, key=lambda item: item['ft'], reverse=True):
            if key == '' or key==p.get('key',''):
                # title
                title = '%s [COLOR khaki]%s[/COLOR] [COLOR khaki](%s)[/COLOR]' % (h.format(p['ft']),p['title'], p['name'])
                # logo
                id = p['gtvid'].split('_')
                logopath = os.path.join(Const.MEDIA_PATH, 'logo_%s_%s.png' % (id[0],id[1]))
                if not os.path.isfile(logopath): logopath = 'DefaultFile.png'
                # listitemを追加
                li = xbmcgui.ListItem(title, iconImage=logopath, thumbnailImage=logopath)
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
