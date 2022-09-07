<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="2.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:itunes="http://www.itunes.com/DTDs/Podcast-1.0.dtd"
  xmlns:dc="http://purl.org/dc/elements/1.1/">
  <xsl:output method="html" version="1.0" encoding="UTF-8" indent="yes"/>
  <xsl:template match="/">
    <html xmlns="http://www.w3.org/1999/xhtml">
      <head>
        <title><xsl:value-of select="/rss/channel/title"/> RSS Feed</title>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <style type="text/css">
          body {
          font-family: Helvetica, Arial, sans-serif;
          font-size: 14px;
          color: #545454;
          background: #E5E5E5;
          line-height: 1.5;
          }
          a, a:link, a:visited {
          color: #005C82;
          text-decoration: none;
          }
          a:hover {
          color: #000;
          }
          h1, h3 {
          margin-top: 0;
          margin-bottom: 20px;
          }
          p.episode-source {
          margin-top: 0;
          margin-bottom: 0px;
          }
          p.episode-date {
          margin-top: 0;
          margin-bottom: 20px;
          }
          h2 {
          margin-top: 0;
          margin-bottom: 0px;
          }
          h3 {
          font-style: italic;
          }
          iframe {
            width: 100%;
            border: none;
          }
          #content {
          width: 700px;
          margin: 0 auto;
          background: #FFF;
          padding: 30px;
          border-radius: 1em;
          box-shadow: 0px 0px 2px #5D5D5D;
          }
          #channel-image {
          float: right;
          width: 200px;
          margin-bottom: 20px;
          }
          #channel-image img {
          width: 200px;
          height: auto;
          border-radius: 5px;
          }
          #channel-header {
          margin-bottom: 20px;
          }
          .channel-item {
          clear: both;
          border-top: 1px solid #E5E5E5;
          padding: 20px;
          }
          .episode-image img {
          width: 100px;
          height: auto;
          margin: 0 30px 15px 0;
          border-radius: 5px;
          }
          .episode-source {
          /*font-size: 11px;*/
          font-weight: bold;
          font-style: italic;
          }
          .episode-date {
          /*font-size: 11px;*/
          font-weight: bold;
          font-style: italic;
          }
          .episode-meta {
          /*font-size: 11px;*/
          font-weight: bold;
          font-style: italic;
          float: right;
          }
        </style>
      </head>
      <body>
        <div id="content">
          <div id="channel-header">
            <h1>
              <xsl:if test="/rss/channel/image">
                <div id="channel-image">
                  <a>
                    <xsl:attribute name="href">
                      <xsl:value-of select="/rss/channel/image/link"/>
                    </xsl:attribute>
                    <img>
                      <xsl:attribute name="src">
                        <xsl:value-of select="/rss/channel/image/url"/>
                      </xsl:attribute>
                      <xsl:attribute name="title">
                        <xsl:value-of select="/rss/channel/image/title"/>
                      </xsl:attribute>
                    </img>
                  </a>
                </div>
              </xsl:if>
              <a>
                <xsl:attribute name="href">
                  <xsl:value-of select="/rss/channel/link"/>
                </xsl:attribute>
                <xsl:value-of select="/rss/channel/title"/>
              </a>
            </h1>
            <p>
              <xsl:value-of select="/rss/channel/description"/>
            </p>
          </div>
          <xsl:for-each select="/rss/channel/item">
            <div class="channel-item">
              <p class="episode-source">
                <xsl:value-of select="source"/>
              </p>
              <h2>
                <xsl:choose>
                  <xsl:when test="link/text()">
                    <a>
                      <xsl:attribute name="href">
                        <xsl:value-of select="link"/>
                      </xsl:attribute>
                      <xsl:attribute name="target">_blank</xsl:attribute>
                      <xsl:value-of select="title"/>
                    </a>
                  </xsl:when>
                  <xsl:otherwise>
                    <xsl:value-of select="title"/>
                  </xsl:otherwise>
                </xsl:choose>
              </h2>
              <p class="episode-date">
                <xsl:value-of select="pubDate"/>
              </p>
              <xsl:if test="description">
                <p>
                  <iframe onload="this.style.height=this.contentWindow.document.body.offsetHeight+20+'px';">
                    <xsl:attribute name="srcdoc">
                      <xsl:value-of select="description" disable-output-escaping="yes"/>
                    </xsl:attribute>
                  </iframe>
                </p>
              </xsl:if>
              <p class="episode-meta">
                <a>
                  <xsl:attribute name="href">
                    <xsl:value-of select="enclosure/@url"/>
                  </xsl:attribute>
                  Download
                </a>
                |
                <xsl:value-of select="itunes:duration"/>
                |
                <xsl:value-of select='format-number(number(enclosure/@length div "1024000"),"0.0")'/>MB
              </p>
            </div>
          </xsl:for-each>
        </div>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
