#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import mechanize
import json

from utils import Utils
from weibo_parser import WeiboCssParser

class NoHistory(object):
    def add(self, *a, **k): pass
    def clear(self): pass

class WeiboDonwloader:
    # get new logger
    logger = logging.getLogger('weibo.WeiboDonwloader')

    def __init__(self, cookies):
        self.cookies = cookies

    def comment_page(self, **keywords):
        url = "http://weibo.com/aj/v6/comment/big?ajwvr=6&id=%s&__rnd=1443108475395&page=%d" \
            % (keywords['mid'], keywords['page'])
        if keywords['page'] > 1 and keywords.has_key('maxid') :
            url = "http://weibo.com/aj/v6/comment/big?ajwvr=6&id=%s&max_id=%s&__rnd=1443108475395&page=%d" \
                % (keywords['mid'], keywords['maxid'], keywords['page'])
        self.logger.info("DOWNLOAD comment %s page %d FROM %s" % (keywords['mid'], keywords['page'], url))
        br = mechanize.Browser(history=NoHistory())
        br.set_cookiejar(self.cookies)
        Utils.add_header(br)
        r = br.open(url)
        html = Utils.ungzip_read(r).decode('raw-unicode-escape')
        commentjson = json.loads(html)
        html = commentjson["data"]["html"].replace('\\r\\n', '').replace("\\n", '').replace("\\t", ' ').decode("string_escape").replace('\/', '/')
        
        start = html.find('max_id=') + 7
        end = html.find('&', start)
        if start != -1 and end != -1:
            return [html], commentjson['data']['page']['totalpage'], html[start:end] 
        return [html], commentjson['data']['page']['totalpage'], None

    def person_page(self, **keywords):
        # change url to v6
        baseurl = 'http://weibo.com/p/aj/v6/mblog/mbloglist?ajwvr=6&domain=100505&pre_page=%d&page=%d&pagebar=%d&pl_name=Pl_Official_MyProfileFeed__24&id=100505%s&script_uri=/p/100505%s&feed_type=0&domain_op=100505&__rnd=1443114844030'
        #baseurl = 'http://weibo.com/p/aj/mblog/mbloglist?domain=100505&pre_page=%d&page=%d&count=15&pagebar=%d&pl_name=Pl_Official_LeftProfileFeed__19&id=100505%s&script_uri=/p/100505%s/weibo'
        self.logger.info("DOWNLOAD user %s page %d" % (keywords['uid'], keywords['page']))
        br = mechanize.Browser(history=NoHistory())
        br.set_cookiejar(self.cookies)
        Utils.add_header(br)
        htmls = []
        for url in [
            baseurl % (keywords['page']-1, keywords['page'], 0, keywords['uid'], keywords['uid']),
            baseurl % (keywords['page'], keywords['page'], 0, keywords['uid'], keywords['uid']),
            baseurl % (keywords['page'], keywords['page'], 1, keywords['uid'], keywords['uid'])
        ]:
            html = self.search_one_block(br, url, 1)
            if html != None:
                htmls.append(html)
        return htmls

    def search_one_block(self, br, url, time):
        if time >= 10:
            time.sleep(300)
            return self.search_one_block(br, url, 1)
        try:
            self.logger.info("DOWNLOAD user page %s" % url)
            r = br.open(url)
            html = Utils.ungzip_read(r).decode("raw-unicode-escape")
            htmljson = json.loads(html)
            if htmljson["code"] == "100001":
                time.sleep(10)
                return self.search_one_block(br, url, time+1)
            bi = html.find(u'<!--feed内容-->')
            if bi != -1:
                text = htmljson['data'].replace('\\r\\n', '').replace("\\n", '').replace("\\t", ' ').decode("string_escape").replace('\/', '/')
                return text 
            else:
                self.logger.error("ERROR html not have '<!--feed内容-->'")
                return None
        except Exception, e:
            self.logger.error('EXCEPTION %s' % str(e))
            return None

    def search_page(self, **keywords):
        url = "http://s.weibo.com/weibo/%s?typeall=1&suball=1&timescope=custom:%s:%s&page=%d" % \
            (keywords['title'], Utils.format_time(keywords['start']), Utils.format_time(keywords['end']), keywords['page'])
        self.logger.info("DOWNLOAD title %s page %d FROM %s" % (keywords['title'], keywords['page'], url))
        br = mechanize.Browser(history=NoHistory())
        br.set_cookiejar(self.cookies)
        Utils.add_header(br)
        return [self.search_one_query(br, url, 1)]

    def search_one_query(self, br, url, time):
        if time >= 10:
            time.sleep(300)
            return self.search_one_query(br, url, 1)
        r = br.open(url)
        html = Utils.ungzip_read(r)
        si = html.find("{\"pid\":\"pl_weibo_direct\"")
        ei = html.find(")</script>", si)
        jsonblock = html[si:ei].decode("raw-unicode-escape")
        htmljson = json.loads(jsonblock)
        text = htmljson['html'].replace('\\r\\n', '').replace("\\n", '').replace("\\t", ' ').decode("string_escape").replace('\/', '/')

        # 未通过审核应用 bug
        bug = text.find('未通过审核应用</a>')
        if bug != -1:
            text = text[0:bug] + '<a>' + text[bug:]
        return text