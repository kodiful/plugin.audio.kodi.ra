# -*- coding: utf-8 -*-

from resources.lib.const import Const
from resources.lib.common import log
from resources.lib.common import notify
from resources.lib.common import strptime
from resources.lib.common import read_json
from resources.lib.common import write_json
from resources.lib.common import timestamp
from resources.lib.localproxy import LocalProxy
from resources.lib.contents import Contents

import datetime
import time
import os
import subprocess
import glob
import re
import threading


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
                if not os.path.isfile(mp3_file):
                    os.remove(json_file)
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
            if p.returncode is None:
                p.kill()

    def status(self, id, ft):
        # 番組ID
        gtvid = '%s_%s' % (id, ft)
        # ファイルパス
        json_file = os.path.join(Const.DOWNLOAD_PATH, '%s.json' % gtvid)
        tmp_file = os.path.join(Const.DOWNLOAD_PATH, '.%s.mp3' % gtvid)
        mp3_file = os.path.join(Const.DOWNLOAD_PATH, '%s.mp3' % gtvid)
        # 既存の番組情報ファイルの有無をチェック
        status = 0
        if os.path.isfile(json_file):
            status += 1
        if os.path.isfile(tmp_file):
            status += 2
        if os.path.isfile(mp3_file):
            status += 4
        return status

    def enqueue(self, id, name, ft, to, title, description, stream, url, delay):
        # 時刻をチェック
        if to < timestamp():
            return 'Already over'
        # 既存の番組情報ファイルの有無をチェック
        status = self.status(id, ft)
        if status & 4:
            return 'Already downloaded'
        if status & 2:
            return 'Already scheduled and now downloading'
        if status & 1:
            return 'Already scheduled'
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
                    id=p['id'],
                    start=p['ft'],
                    title=p['title'],
                    keyword=k['key']))
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
                        id=p['id'],
                        start=p['ft'],
                        title=p['title'],
                        keyword=k['key']))
                # 次の番組のダウンロード処理へ
                continue
            # Const.PREP_INTERVAL以降に開始する番組
            else:
                # ダウンロード待ちの番組としてリストに追加
                remaining.append(m)
        self.pending = remaining

    def start(self, id, name, ft, to, title, description, stream, delay, url='', key=''):
        # 番組ID
        gtvid = '%s_%s' % (id, ft)
        # ファイルパス
        json_file = os.path.join(Const.DOWNLOAD_PATH, '%s.json' % gtvid)
        tmp_file = os.path.join(Const.DOWNLOAD_PATH, '.%s.mp3' % gtvid)
        mp3_file = os.path.join(Const.DOWNLOAD_PATH, '%s.mp3' % gtvid)
        # 現在時刻
        now = datetime.datetime.now()
        # 開始時間
        start = strptime(ft, '%Y%m%d%H%M%S')
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
        # ソースのURL
        stream, headers = LocalProxy.parse(stream)
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
        # ダウンロード実行のパラメータ
        data = {
            'ffmpeg': Const.GET('ffmpeg'),
            'wait': wait,
            'start': start,
            'duration': duration,
            'stream': stream,
            'headers': headers,
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
        # 別スレッドでダウンロード実行
        t = threading.Thread(target=self.__thread, args=[data])
        t.start()
        self.thread.append(t)

    def __thread(self, data):
        # ヘッダ
        headers = ''
        for key, val in data['headers'].items():
            headers += '%s: %s\r\n' % (key, val)
        # コマンドライン
        template = '"{ffmpeg}" -y -v warning -t {duration} -headers "{headers}" -i "{stream}" -acodec libmp3lame -b:a {bitrate} ' \
            '-metadata title="{title}" ' \
            '-metadata artist="{artist}" ' \
            '-metadata copyright="{copyright}" ' \
            '-metadata publisher="{publisher}" ' \
            '-metadata date="{date}" ' \
            '-metadata TIT1="{tit1}" ' \
            '-metadata TIT3="{tit3}" ' \
            '"{tmp_file}"'
        command = template.format(
            ffmpeg=data['ffmpeg'],
            duration=data['duration'],
            headers=headers,
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
                # 全コンテンツのrssファイル生成
                Contents().createrss()
                # 対応するkey(=data['tit1'])のコンテンツrssファイル生成
                if data['tit1']:
                    Contents(data['tit1']).createrss()
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
