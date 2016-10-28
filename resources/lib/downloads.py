# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import datetime, time
import os, platform, subprocess, commands
import sys, glob, shutil
import codecs
import json
import re
import urllib2
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

from datetime import datetime

from resources.lib.common import(
    __addon_id__,
    __settings__,
    __media_path__,
    __plugin_path__,
    __template_path__)

from resources.lib.common import(
    __download_path__,
    __exit_file__,
    __rss_file__,
    __rss_url__)

from resources.lib.common import(
    __margin_interval__)

from resources.lib.common import(log)
from resources.lib.common import(strptime)

class Downloads:

    def __init__(self):
        self.os = platform.system()
        self.rtmpdump = __settings__.getSetting('rtmpdump')
        self.ffmpeg = __settings__.getSetting('ffmpeg')
        # templates
        f = codecs.open(os.path.join(__template_path__,'template.json'),'r','utf-8')
        self.template = f.read()
        f.close()

    def add(self, id, name, start, end, prog, desc, options, key=''):
        # OS判定
        if self.os == 'Windows':
            log1_file = 'NUL'
            log2_file = 'NUL'
        elif self.os == 'Darwin':
            log1_file = '/dev/null'
            log2_file = '/dev/null'
        else:
            return {'status':False, 'message':'Failed. Unsupported OS'}
        # 番組ID
        gtvid = '%s_%s' % (id,start);
        # ファイルパス
        js_file  = os.path.join(__download_path__, gtvid+'.js')
        mp3_file = os.path.join(__download_path__, gtvid+'.mp3')
        # 番組情報の有無をチェック
        if os.path.isfile(js_file):
            return {'status':False, 'message':'Failed. Saved data exists'}
        # 現在時刻
        now1 = datetime.now()
        # 開始時間
        start1 = strptime(start, '%Y%m%d%H%M%S')
        startdate = start1.strftime('%Y-%m-%d %H:%M:%S')
        # 終了時間
        end1 = strptime(end, '%Y%m%d%H%M%S')
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
                return {'status':False, 'message':'Failed. Program is over'}
        # 録音時間
        duration = end1 - start1
        if duration.seconds > 0:
            if wait == 0:
                duration = duration.seconds + __margin_interval__
            else:
                if wait > __margin_interval__:
                    duration = duration.seconds + __margin_interval__ + __margin_interval__
                    wait = wait - __margin_interval__
                else:
                    duration = duration.seconds + wait + __margin_interval__
                    wait = 0
        else:
            # durationが異常値
            return {'status':False, 'message':'Failed. Invalid start and/or end'}
        # 番組情報を保存
        js_data = self.template.format(
            gtvid=gtvid,
            startdate=startdate,
            duration=duration1.seconds,
            ch=id,
            title=prog.replace('&amp;','&').replace('&','&amp;'),
            description=desc.replace('&amp;','&').replace('&','&amp;'),
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
        rtmpdump += '"{ffmpeg}" -i pipe:0 -acodec libmp3lame -b:a 192k -metadata title="{title}" -metadata artist="{artist}" -metadata copyright="{copyright}" -metadata publisher="{publisher}" -metadata date="{date}" -metadata TIT1="{tit1}" -metadata TIT3="{tit3}" "{mp3}" 2> "{log2}"'.format(
            ffmpeg=self.ffmpeg,
            title=prog,
            artist=name,
            copyright=name,
            publisher=name,
            date=start1.strftime('%Y-%m-%dT%H:%M:%SZ'),
            tit1=key,
            tit3=desc,
            mp3=mp3_file,
            log2=log2_file)
        # スクリプト作成
        if self.os == 'Darwin':
            sh_file  = os.path.join(__download_path__, gtvid+'.sh')
            # sh
            command = []
            command.append('cd "%s"' % (__download_path__))
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
            bat_file  = os.path.join(__download_path__, gtvid+'.bat')
            # bat
            command = []
            command.append('CD "%s"' % (__download_path__))
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
        log('%s %s' % (gtvid,prog))
        return {'status':True, 'message':'Download started/reserved successfully'}

    def deleteall(self):
        # 実行中のプロセスを停止
        for file in glob.glob(os.path.join(__download_path__, '*.pid')):
            gtvid = file.replace(__download_path__,'').replace('.pid','')
            self.kill(gtvid)
        # ファイル削除
        for file in glob.glob(os.path.join(__download_path__, '*.*')):
            if os.path.isfile(file): os.remove(file)
        # rssファイル生成
        self.createRSS()
        # 再表示
        xbmc.executebuiltin('XBMC.Container.Update(%s,replace)' % (sys.argv[0]))
        return {'status':True, 'message':'Saved data deleted successfully'}

    def delete(self, gtvid):
        # 実行中のプロセスを停止
        if self.kill(gtvid):
            # ファイル削除
            for file in glob.glob(os.path.join(__download_path__, '%s.*' % (gtvid))):
                if os.path.isfile(file): os.remove(file)
            # rssファイル生成
            self.createRSS()
            # 再表示
            xbmc.executebuiltin("XBMC.Container.Refresh")
            return {'status':True, 'message':'Saved data deleted successfully'}
        else:
            return {'status':False, 'message':'Failed. Now recording'}

    def kill(self, gtvid):
        pid_file = os.path.join(__download_path__, '%s.pid' % (gtvid))
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
        for file in glob.glob(os.path.join(__download_path__, '*.js')):
            js_file = os.path.join(__download_path__, file)
            mp3_file = os.path.join(__download_path__, file.replace('.js','.mp3'))
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
                logopath = os.path.join(__media_path__, 'logo_%s_%s.png' % (id[0],id[1]))
                if not os.path.isfile(logopath): logopath = 'DefaultFile.png'
                # listitemを追加
                li = xbmcgui.ListItem(title, iconImage=logopath, thumbnailImage=logopath)
                li.setInfo(type='music', infoLabels={'title':p['title'],'duration':p['duration'],'artist':p['bc'],'comment':p['description']})
                li.setProperty('IsPlayable', 'true')
                # context menu
                li.addContextMenuItems([(__settings__.getLocalizedString(30314), 'XBMC.RunPlugin(%s?action=deleteDownload&id=%s)' % (sys.argv[0],p['gtvid']))], replaceItems=True)
                # add directory item
                # file
                mp3_file = os.path.join(__download_path__, p['gtvid'] + '.mp3')
                xbmcplugin.addDirectoryItem(int(sys.argv[1]), mp3_file, li, isFolder=False)
        xbmcplugin.endOfDirectory(int(sys.argv[1]), succeeded=True)

    def createRSS(self):
        if __settings__.getSetting('rss') == 'false': return
        # templates
        f = codecs.open(os.path.join(__template_path__,'rss-header.xml'),'r','utf-8')
        header = f.read()
        f.close()
        f = codecs.open(os.path.join(__template_path__,'rss-body.xml'),'r','utf-8')
        body = f.read()
        f.close()
        f = codecs.open(os.path.join(__template_path__,'rss-footer.xml'),'r','utf-8')
        footer = f.read()
        f.close()
        # open rss
        rss = codecs.open(__rss_file__,'w','utf-8')
        # header
        rss.write(
            header.format(
                image=__rss_url__+'icon.png'))
        # body
        plist = []
        for file in glob.glob(os.path.join(__download_path__, '*.js')):
            js_file = os.path.join(__download_path__, file)
            mp3_file = os.path.join(__download_path__, file.replace('.js','.mp3'))
            pid_file = os.path.join(__download_path__, file.replace('.js','.pid'))
            if not os.path.isfile(pid_file) and os.path.isfile(mp3_file):
                f = codecs.open(os.path.join(__download_path__,file),'r','utf-8')
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
            url = __rss_url__ + gtvid + '.mp3'
            # file
            mp3_file = os.path.join(__download_path__, gtvid + '.mp3')
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
        dst = os.path.join(__download_path__, 'icon.png')
        if os.path.isfile(dst): os.remove(dst)
        src = os.path.join(__plugin_path__, 'icon.png')
        shutil.copy(src, dst)
        # copy script if necessary
        dst = os.path.join(__download_path__, 'rss.php')
        if os.path.isfile(dst): os.remove(dst)
        src = os.path.join(__template_path__, 'rss.php')
        shutil.copy(src, dst)
