<?php

// RSSのテンプレート

$header = <<<EOF
<?xml version="1.0" encoding="UTF-8"?>
<rss
    xmlns:itunes="http://www.itunes.com/DTDs/Podcast-1.0.dtd"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:media="http://search.yahoo.com/mrss"
    version="2.0" xml:lang="ja">
  <channel>
    <ttl>60</ttl>
    <title>KodiRa</title>
    <link></link>
    <language>ja</language>
    <copyright></copyright>
    <description></description>
    <image>
      <url>{image}</url>
      <link></link>
      <title>KodiRa</title>
    </image>
    <itunes:image href="{image}" />
EOF;

$body = <<<EOF
    <item>
      <title>{title}</title>
      <link>{url}</link>
      <description>{description}</description>
      <category></category>
      <pubDate>{startdate}</pubDate>
      <guid>{gtvid}</guid>
      <source>{bc}</source>
      <author>{bc}</author>
      <enclosure url="{url}" length="{filesize}" type="audio/mp3" />
      <itunes:explicit>no</itunes:explicit>
      <itunes:duration>{duration}</itunes:duration>
      <itunes:summary>{description}</itunes:summary>
      <itunes:author>{bc}</itunes:author>
      <dc:creator>{bc}</dc:creator>
    </item>
EOF;

$footer = <<<EOF
  </channel>
</rss>
EOF;

// URLから抽出

if($_SERVER['HTTPS']) {
  $url = "https://";
} else {
  $url = "http://";
}
$url .= $_SERVER['SERVER_NAME'];
if($_SERVER['SERVER_PORT'] != '80') {
  $url .= ":" . $_SERVER['SERVER_PORT'];
}
$url .= preg_replace('/rss\.php$/', '', $_SERVER['SCRIPT_NAME']);
$dir =  preg_replace('/rss\.php$/', '', $_SERVER['SCRIPT_FILENAME']);

// HTTPヘッダを出力
header("Content-Type: text/xml");

// RSSヘッダを出力
echo str_replace("{image}", $url . "icon.png", $header);

// このスクリプトと同じディレクトリに格納されているファイルをチェック
foreach (glob("*.mp3") as $filename) {
  $filename = preg_replace('/\.mp3$/', '', $filename);
  if(file_exists($filename . ".pid")) {
    // ダウンロード中のファイルはスキップ
  } else if(file_exists($filename . ".js")) {
    // メタデータを取得
    $json = json_decode(file_get_contents($filename . ".js"), true);
    // クエリとメタデータを照合
    $hit = TRUE;
    if(isset($_GET['title_or_description'])) {
      if(strpos($json['program'][0]['title'], $_GET['title_or_description']) !== FALSE
        or strpos($json['program'][0]['description'], $_GET['title_or_description']) !== FALSE) {
        $hit = TRUE;
      } else {
        $hit = FALSE;
      }
    }
    if(isset($_GET['title'])) {
      if($hit and strpos($json['program'][0]['title'], $_GET['title']) !== FALSE) {
        $hit = TRUE;
      } else {
        $hit = FALSE;
      }
    }
    if(isset($_GET['description'])) {
      if($hit and strpos($json['program'][0]['description'], $_GET['title']) !== FALSE) {
        $hit = TRUE;
      } else {
        $hit = FALSE;
      }
    }
    if(isset($_GET['bc'])) {
      if($hit and strpos($json['program'][0]['bc'], $_GET['title']) !== FALSE) {
        $hit = TRUE;
      } else {
        $hit = FALSE;
      }
    }
    if($hit) {
      // RSSボディを出力
      $source = $body;
      $source = str_replace("{title}", $json['program'][0]['title'], $source);
      $source = str_replace("{url}", $url . $filename . ".mp3", $source);
      $source = str_replace("{description}", $json['program'][0]['description'], $source);
      $source = str_replace("{gtvid}", $json['program'][0]['gtvid'], $source);
      $source = str_replace("{bc}", $json['program'][0]['bc'], $source);
      $source = str_replace("{filesize}", filesize($filename . ".mp3"), $source);
      // startdate
      $startdate = strftime('%a, %d %b %Y %H:%M:%S +0900', strtotime($json['program'][0]['startdate']));
      $source = str_replace("{startdate}", $startdate, $source);
      // duration
      $duration = $json['program'][0]['duration'];
      $duration = sprintf("%02d:%02d:%02d", intval($duration/3600), intval($duration/60)%60, $duration%60);
      $source = str_replace("{duration}", $duration, $source);
      echo $source, "\n";
    }
  }
}

// RSSフッタを出力
echo $footer;

?>
