# -*- coding: utf-8 -*-

import resources.lib.common as common
from resources.lib.common import(log,notify)
from resources.lib.common import(strptime)

import datetime, time
import os, platform, subprocess, commands
import sys, glob, shutil
import codecs
import json
import re
import urllib2
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

from datetime import datetime

class Downloads:

    def __init__(self):
        self.os = platform.system()
        self.rtmpdump = common.addon.getSetting('rtmpdump')
        self.ffmpeg = common.addon.getSetting('ffmpeg')
        # templates
        f = codecs.open(os.path.join(common.template_path,'template.json'),'r','utf-8')
        self.template = f.read()
        f.close()

    def add(self, id, name, start, end, title, description, options, key=''):
        # OS判定
        if self.os == 'Windows':
            log1_file = 'NUL'
            log2_file = 'NUL'
        elif self.os == 'Darwin':
            log1_file = '/dev/null'
            log2_file = '/dev/null'
        else:
            notify('Download failed. Unsupported OS.', error=True)
            return
        # 番組ID
        gtvid = '%s_%s' % (id,start);
        # ファイルパス
        js_file  = os.path.join(common.download_path, gtvid+'.js')
        mp3_file = os.path.join(common.download_path, gtvid+'.mp3')
        # 番組情報の有無をチェック
        if os.path.isfile(js_file):
            notify('Download failed. Saved data exists.', error=True)
        # 現在時刻
        now1 = datetime.now()
        # 開始時間
        start1 = strptime(start, '%Y%m%d%H%M%S')
        startdate = start1.strftime('%Y-%m-%d %H:%M:%S')
        # 終了時間
        end1 = strptime(end, '%Y%m%d%H%M%S')
        # ラグ調整
        lag = datetime.timedelta(seconds=common.lag)
        start1 = start1 + lag
        end1 = end1 + lag
        # 放送時間
        duration1 = end1 - start1
        # 録音開始の設定
        if start1 > now1:
            # まだ始まっていない場合は開始を待つ
            wait = start1 - now1
            wait = wait.seconds
        else:
            # すでに始まっている場合
            if end1 > now1:
                # まだ終わっていない場合はすぐ開始する
                start1 = now1
                wait = 0
            else:
                # すでに終わっている場合はこのまま終了する
                notify('Download failed. Program is over.', error=True)
                return
        # 録音時間
        duration = end1 - start1
        if duration.seconds > 0:
            if wait == 0:
                # すぐ開始する場合
                duration = duration.seconds + common.margin_interval
            else:
                if wait > common.margin_interval:
                    duration = duration.seconds + common.margin_interval + common.margin_interval
                    wait = wait - common.margin_interval
                else:
                    duration = duration.seconds + wait + common.margin_interval
                    wait = 0
        else:
            # durationが異常値
            notify('Download failed. Invalid start and/or end.', error=True)
            return
        # ビットレート
        bitrate = common.addon.getSetting('bitrate')
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
        # 番組情報を保存
        js_data = self.template.format(
            gtvid=gtvid,
            startdate=startdate,
            duration=duration1.seconds,
            ch=id,
            title=title.replace('&lt;','<').replace('&gt;','>').replace('&quot;','"').replace('&amp;','&').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;'),
            description=description.replace('&lt;','<').replace('&gt;','>').replace('&quot;','"').replace('&amp;','&').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;'),
            bc=name,
            key=key)
        f = codecs.open(js_file, 'w', 'utf-8')
        f.write(js_data)
        f.close()
        # コマンドライン
        rtmpdump = '"{rtmpdump}" {options} -B {duration} 2> "{log1}"'.format(
            rtmpdump=self.rtmpdump,
            options=options,
            duration=duration,
            log1=log1_file)
        rtmpdump += '|'
        rtmpdump += '"{ffmpeg}" -i pipe:0 -acodec libmp3lame -b:a {bitrate} -metadata title="{title}" -metadata artist="{artist}" -metadata copyright="{copyright}" -metadata publisher="{publisher}" -metadata date="{date}" -metadata TIT1="{tit1}" -metadata TIT3="{tit3}" "{mp3}" 2> "{log2}"'.format(
            ffmpeg=self.ffmpeg,
            bitrate=bitrate,
            title=title,
            artist=name,
            copyright=name,
            publisher=name,
            date=start1.strftime('%Y-%m-%dT%H:%M:%SZ'),
            tit1=key,
            tit3=description,
            mp3=mp3_file,
            log2=log2_file)
        # スクリプト作成
        if self.os == 'Darwin':
            sh_file  = os.path.join(common.download_path, gtvid+'.sh')
            # sh
            command = []
            command.append('cd "%s"' % (common.download_path))
            command.append('echo $$ > %s.pid' % (gtvid))
            command.append('sleep %d' % (wait))
            command.append(rtmpdump)
            command.append('rm -f %s.pid' % (gtvid))
            command.append('echo $$ > exit')
            f = codecs.open(sh_file, 'w', 'utf-8')
            f.write('\n'.join(command))
            f.close()
            # スクリプト実行
            proc = subprocess.Popen('sh "%s"' % (sh_file), shell=True)
        elif self.os == 'Windows':
            bat_file  = os.path.join(common.download_path, gtvid+'.bat')
            # bat
            command = []
            command.append('CD "%s"' % (common.download_path))
            command.append('ECHO > %s.pid' % (gtvid))
            command.append('TIMEOUT /T %d /NOBREAK > NUL' % (wait))
            command.append(rtmpdump)
            command.append('DEL %s.pid' % (gtvid))
            command.append('ECHO > exit')
            f = codecs.open(bat_file, 'w', 'shift_jis', 'ignore')
            f.write('\r\n'.join(command))
            f.close()
            # スクリプト実行
            proc = subprocess.Popen(bat_file, shell=True)
        # ログ
        log('%s %s' % (gtvid,title))

    def deleteall(self):
        # 実行中のプロセスを停止
        status = True
        for file in glob.glob(os.path.join(common.download_path, '*.pid')):
            gtvid = file.replace(common.download_path,'').replace('.pid','')
            status = status and self.kill(gtvid)
        if status == False:
            notify('Download failed. Now recording.', error=True)
            return
        # ファイル削除
        for file in glob.glob(os.path.join(common.download_path, '*.*')):
            if os.path.isfile(file): os.remove(file)
        # rssファイル生成
        self.createRSS()
        # 再表示
        xbmc.executebuiltin('Container.Update(%s,replace)' % (sys.argv[0]))

    def delete(self, gtvid):
        # 実行中のプロセスを停止
        if self.kill(gtvid) == False:
            notify('Download failed. Now recording.', error=True)
            return
        # ファイル削除
        for file in glob.glob(os.path.join(common.download_path, '%s.*' % (gtvid))):
            if os.path.isfile(file): os.remove(file)
        # rssファイル生成
        self.createRSS()
        # 再表示
        xbmc.executebuiltin("Container.Refresh")

    def kill(self, gtvid):
        pid_file = os.path.join(common.download_path, '%s.pid' % (gtvid))
        if os.path.isfile(pid_file):
            if self.os == 'Darwin':
                # 親プロセスのpidを取得する
                f = codecs.open(pid_file, 'r', 'utf-8')
                ppid = int(f.read())
                f.close()
                # pidの子プロセスを抽出
                cpid = commands.getoutput('ps -A -o ppid,pid | awk "\$1==%d{print \$2}"' % (ppid)).replace('\n',' ')
                os.system('kill %s %d' % (cpid,ppid))
                return True
            else:
                return False
        else:
            return True

    def show(self, key=''):
        plist = []
        for file in glob.glob(os.path.join(common.download_path, '*.js')):
            js_file = os.path.join(common.download_path, file)
            mp3_file = os.path.join(common.download_path, file.replace('.js','.mp3'))
            if os.path.isfile(mp3_file):
                f = codecs.open(js_file,'r','utf-8')
                plist.append(json.loads(f.read())['program'][0])
                f.close()
        # 時間の逆順にソート
        plist = sorted(plist, key=lambda item: item['startdate'])
        plist.reverse()
        # 表示
        for p in plist:
            try:
                p['key']
            except:
                p['key'] = ''
            if key == '' or key==p['key']:
                # title
                title = '[COLOR white]%s[/COLOR] [COLOR khaki]%s[/COLOR] [COLOR lightgreen](%s)[/COLOR]' % (p['startdate'],p['title'],p['bc'])
                # logo
                id = p['gtvid'].split('_')
                logopath = os.path.join(common.media_path, 'logo_%s_%s.png' % (id[0],id[1]))
                if not os.path.isfile(logopath): logopath = 'DefaultFile.png'
                # listitemを追加
                li = xbmcgui.ListItem(title, iconImage=logopath, thumbnailImage=logopath)
                #li.setInfo(type='music', infoLabels={'title':p['title'],'duration':p['duration'],'artist':p['bc'],'comment':p['description']})
                comment = p['description']
                comment = re.sub(r'&lt;.*?&gt;','\n', comment)
                comment = re.sub(r'\n{2,}', '\n', comment)
                comment = re.sub(r'^\n+', '', comment)
                comment = re.sub(r'\n+$', '', comment)
                li.setInfo(type='music', infoLabels={'title':p['title'],'duration':p['duration'],'artist':p['bc'],'comment':comment})
                li.setProperty('IsPlayable', 'true')
                # context menu
                li.addContextMenuItems([(common.addon.getLocalizedString(30314), 'RunPlugin(%s?action=deleteDownload&id=%s)' % (sys.argv[0],p['gtvid']))], replaceItems=True)
                # add directory item
                # file
                mp3_file = os.path.join(common.download_path, p['gtvid'] + '.mp3')
                xbmcplugin.addDirectoryItem(int(sys.argv[1]), mp3_file, li, isFolder=False)
        xbmcplugin.endOfDirectory(int(sys.argv[1]), succeeded=True)

    def createRSS(self):
        if common.addon.getSetting('rss') == 'false': return
        # templates
        f = codecs.open(os.path.join(common.template_path,'rss-header.xml'),'r','utf-8')
        header = f.read()
        f.close()
        f = codecs.open(os.path.join(common.template_path,'rss-body.xml'),'r','utf-8')
        body = f.read()
        f.close()
        f = codecs.open(os.path.join(common.template_path,'rss-footer.xml'),'r','utf-8')
        footer = f.read()
        f.close()
        # open rss
        rss = codecs.open(common.rss_file,'w','utf-8')
        # header
        rss.write(
            header.format(
                image=common.rss_url+'icon.png'))
        # body
        plist = []
        for file in glob.glob(os.path.join(common.download_path, '*.js')):
            js_file = os.path.join(common.download_path, file)
            mp3_file = os.path.join(common.download_path, file.replace('.js','.mp3'))
            pid_file = os.path.join(common.download_path, file.replace('.js','.pid'))
            if not os.path.isfile(pid_file) and os.path.isfile(mp3_file):
                f = codecs.open(os.path.join(common.download_path,file),'r','utf-8')
                plist.append(json.loads(f.read())['program'][0])
                f.close()
        # sort by startdate in reverse order
        plist = sorted(plist, key=lambda item: item['startdate'])
        plist.reverse()
        # build
        for p in plist:
            # gtvid
            gtvid = p['gtvid']
            # url
            url = common.rss_url + gtvid + '.mp3'
            # file
            mp3_file = os.path.join(common.download_path, gtvid + '.mp3')
            # startdate
            startdate = strptime(p['startdate'],'%Y-%m-%d %H:%M:%S').strftime('%a, %d %b %Y %H:%M:%S +0900')
            # duration
            duration = int(p['duration'])
            duration = '%02d:%02d:%02d' % (int(duration/3600),int(duration/60)%60,duration%60)
            # filesize
            if os.path.isfile(mp3_file):
                filesize = os.path.getsize(mp3_file)
            else:
                filesize = 0
            rss.write(
                body.format(
                    title=p['title'],
                    gtvid=gtvid,
                    url=url,
                    startdate=startdate,
                    bc=p['bc'],
                    duration=duration,
                    filesize=filesize,
                    description=p['description']))
        # footer
        rss.write(footer)
        # close rss
        rss.close()
        # copy image if necessary
        dst = os.path.join(common.download_path, 'icon.png')
        if os.path.isfile(dst): os.remove(dst)
        src = os.path.join(common.plugin_path, 'icon.png')
        shutil.copy(src, dst)
        # copy script if necessary
        dst = os.path.join(common.download_path, 'rss.php')
        if os.path.isfile(dst): os.remove(dst)
        src = os.path.join(common.template_path, 'rss.php')
        shutil.copy(src, dst)
