#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bs4 import Tag
from bs4 import NavigableString
from datetime import *
from dateutil.tz import *
import copy
from StringIO import StringIO
from cStringIO import StringIO as cSIO
import gzip
import re
import json
import logging
import random
import time
import cookielib

class CJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        elif isinstance(obj, str):
            return obj.strip()
        else:
            return json.JSONEncoder.default(self, obj)

    def __str_encode(self, obj):
        if isinstance(obj, dict):
            for k,v in obj.iteritems():
                obj[k] = self.__str_encode(v)
        elif isinstance(obj, list):
            for k in range(len(obj)):
                obj[k] = self.__str_encode(obj[k])
        elif isinstance(obj, str):
            obj = obj.strip()
        return obj

    def encode(self, obj):
        """
        encode method gets an original object
        and returns result string. obj argument will be the
        object that is passed to json.dumps function
        """
        result = self.__str_encode(obj)
        return json.JSONEncoder.encode(self, result) 

class jsonS:
    @staticmethod
    def byteify(input):
        if isinstance(input, dict):
            return {jsonS.byteify(key):jsonS.byteify(value) for key,value in input.iteritems()}
        elif isinstance(input, list):
            return [jsonS.byteify(element) for element in input]
        elif isinstance(input, unicode):
            return input.encode('utf-8')
        else:
            return input
    
    @staticmethod
    def load(file):
        return jsonS.byteify(json.load(file))

class Utils:
    logger = logging.getLogger('weibo.Utils')

    HEADER_LIST = [
        ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'),
        ('Accept-Encoding', 'gzip, deflate, sdch'),
        ('Accept-Language', 'zh-CN,zh;q=0.8'),
        ('Cache-Control', 'no-cache'),
        ('Connection', 'keep-alive'),
        ('Host', 'weibo.com'),
        ('Pragma', 'no-cache'),
        ('Upgrade-Insecure-Requests', '1'),
        ('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.85 Safari/537.36')
    ]

    @staticmethod
    def open_retry(browser, url, retry):
        re = 0
        while True: # retry request
            try:
                r = browser.open(url)
            except Exception as e: 
                if re >= retry:
                    if re > 0:
                        Utils.logger.info('RETRY FAIL %s %d' % (url, re))
                    raise e
                re += 1                
                time.sleep(5)
                Utils.logger.info('RETRY %s %d times' % (url, re))
            else:
                return r

    @staticmethod
    def save_cookies_lwp(cookiejar, filename):
        lwp_cookiejar = cookielib.LWPCookieJar()
        for c in cookiejar:
            args = dict(vars(c).items())
            args['rest'] = args['_rest']
            del args['_rest']
            c = cookielib.Cookie(**args)
            lwp_cookiejar.set_cookie(c)
        lwp_cookiejar.save(filename, ignore_discard=True)

    @staticmethod
    def load_cookies_from_lwp(filename):
        lwp_cookiejar = cookielib.LWPCookieJar()
        lwp_cookiejar.load(filename, ignore_discard=True)
        return lwp_cookiejar

    @staticmethod
    def sleep(min, max):
        time.sleep(random.randint(min, max))

    @staticmethod
    def time_flate(num, size):
        num = str(num)
        if len(num) < size:
            return '0' * (size - len(num)) + num
        return num

    @staticmethod
    def get_localtime(year, month, day, hour, minute=0):
        #return datetime.now(tzlocal()).replace(year = year).replace(month = month) \
        #    .replace(day = day).replace(hour = hour).replace(minute = minute)
        return datetime(year, month, day, hour, minute, 0, 0, tzlocal())

    @staticmethod
    def parse_time_text(timetxt):
        now = datetime.now(tzlocal())
        trans = now
        if timetxt.find(u'秒') != -1:
            trans = now - timedelta(seconds=Utils.parse_num(timetxt))
        elif timetxt.find(u'分钟前') != -1:
            trans = now - timedelta(minutes=Utils.parse_num(timetxt))
        elif timetxt.find(u'今天') != -1:
            t = timetxt.replace(u'今天', '').strip().split(':')
            trans = now.replace(hour = int(t[0]), minute = int(t[1]))
        elif timetxt.find(u'月') != -1 and timetxt.find(u'日') != -1:
            t =[int(tt) for tt in filter(Utils.filter_empty, re.split(u'月|日|:| ', timetxt))]
            trans = now.replace(month=t[0], day=t[1], hour=t[2], minute=t[3])
        else:
            trans = Utils.parse_time(timetxt)
        return trans
        #now = datetime.now(tzlocal())
        #timetxt.replace(u'今天', str(now.month) + u'月' + str(now.day) + u'日')
        #if timetxt.find(u'年') == -1:
        #    timetxt = str(now.year) + '年' + str(timetxt)
        #return timetxt

    @staticmethod
    def filter_empty(a):
        if a != '':
            return True
        return False

    @staticmethod
    def parse_time(timestr):

        s = re.split('-|:| ', timestr.strip())
        return Utils.get_localtime(*[int(t) for t in filter(Utils.filter_empty, s)])

    @staticmethod
    def format_time(dt):
        return '-'.join([
            Utils.time_flate(dt.year, 4), 
            Utils.time_flate(dt.month, 2), 
            Utils.time_flate(dt.day, 2), 
            Utils.time_flate(dt.hour, 2)
        ])

    @staticmethod
    def add_header(browser):
        browser.addheaders = copy.deepcopy(Utils.HEADER_LIST)

    @staticmethod
    def ungzip_read(res):
        if res.info().get('Content-Encoding') == 'gzip':
            buf = StringIO(res.read())
            f = gzip.GzipFile(fileobj=buf)
            return f.read()
        return res.read()

    @staticmethod
    def get_innerhtml(node):
        return ' '.join([str(ch) for ch in node.contents])

    @staticmethod
    def get_text(node):
        str = ""
        for con in node.contents:
            if isinstance(con, Tag):
                str = str + ' ' + con.text
            elif isinstance(con, NavigableString):
                str = str + ' ' + con
        return str

    @staticmethod
    def parse_num(nodestr):
        if nodestr == None:
            nodestr = ''
        return int(re.findall(r'\d+', nodestr)[0]) if len(re.findall(r'\d+', nodestr)) == 1 else 0

    @staticmethod
    def get_uid_from_tfinfo(tfinfo):
        for s in tfinfo.split('&'):
            if s.startswith('ouid='):
                return s[5:]
        return None

    @staticmethod
    def parse_input_date(datestr):
        return Utils.get_localtime(*[int(t) for t in datestr.split('-')])

    @staticmethod
    def getfilename(filename, param):
        result = cSIO()
        track = cSIO()
        stop = False
        stack = []
        for i in range(len(filename)):
            if filename[i] == '{':
                stop = True
            if not stop:
                result.write(filename[i])
            else:
                track.write(filename[i])
            if filename[i] == '}':
                stop = False
                pa = track.getvalue()
                result.write(param[pa[1:len(pa)-1]])
                track = cSIO()
        return result.getvalue()

