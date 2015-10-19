#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import base64
import urllib
import urllib2
import re
import json
import random
import rsa
import binascii
import time
import logging
import cookielib
from bs4 import BeautifulSoup

from page_downloader import WeiboDonwloader
from weibo_parser import WeiboCssParser
from weibo import Weibo
from utils import Utils

# use all the header a normal browser would use
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

class WeiboUser:
	logger = logging.getLogger('weibo.WeiboUser')
	
	USER_AGENT = (
		'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/536.11 (KHTML, like Gecko) '
		'Chrome/20.0.1132.57 Safari/536.11'
	)
	WBCLIENT = 'ssologin.js(v1.4.11)'

	def __init__(self, cookies=None):
		self.cookies = cookies

	def encrypt_passwd(self, passwd, pubkey, servertime, nonce):
		key = rsa.PublicKey(int(pubkey, 16), int('10001', 16))
		message = str(servertime) + '\t' + str(nonce) + '\n' + str(passwd)
		passwd = rsa.encrypt(message, key)
		return binascii.b2a_hex(passwd)
	
	def wblogin(self, username, password):
		session = requests.session()
		session.headers['User-Agent'] = WeiboUser.USER_AGENT
		resp = session.get(
			'http://login.sina.com.cn/sso/prelogin.php?'
			'entry=sso&callback=sinaSSOController.preloginCallBack&'
			'su=%s&rsakt=mod&client=%s' %
			(base64.b64encode(username), WeiboUser.WBCLIENT)
		)
		pre_login_str = re.match(r'[^{]+({.+?})', resp.content).group(1)
		pre_login = json.loads(pre_login_str)
		data = {
			'entry': 'weibo',
			'gateway': 1,
			'from': '',
			'savestate': 7,
			'userticket': 1,
			'ssosimplelogin': 1,
			'su': base64.b64encode(urllib.quote(username)),
			'service': 'miniblog',
			'servertime': pre_login['servertime'],
			'nonce': pre_login['nonce'],
			'vsnf': 1,
			'vsnval': '',
			'pwencode': 'rsa2',
			'sp': self.encrypt_passwd(password, pre_login['pubkey'],
								 pre_login['servertime'], pre_login['nonce']),
			'rsakv' : pre_login['rsakv'],
			'encoding': 'UTF-8',
			'prelt': '115',
			'url': 'http://weibo.com/ajaxlogin.php?framelogin=1&callback=parent.si'
				   'naSSOController.feedBackUrlCallBack',
			'returntype': 'META',
		}
		resp = session.post(
			'http://login.sina.com.cn/sso/login.php?client=%s' % WeiboUser.WBCLIENT, data=data
		)
		
		while resp.content.find('code=0') < 0:
			rint = int(random.random()*100000000)
			img = session.get('http://login.sina.com.cn/cgi/pin.php?r=%d&s=0&p=%s' % (rint, pre_login['pcid']))
			fout = open('code.png', 'wb')
			fout.write(img.content)
			fout.close()
			
			data['pcid'] = pre_login['pcid']
			data['door'] = raw_input('%s identifying code >>' % username)
			data['sp'] = self.encrypt_passwd(password, pre_login['pubkey'], pre_login['servertime'], pre_login['nonce'])
			
			resp = session.post(
				'http://login.sina.com.cn/sso/login.php?client=%s' % WeiboUser.WBCLIENT, data=data
			)
			
		login_url = re.search(r'replace\([\"\']([^\'\"]+)[\"\']', resp.content)
		login_url = login_url.group(1)
		resp = session.get(login_url)
		#cPickle_dump('../cookies/cookies_%s.sqlite'%username, resp.cookies)
		self.logger.info('LOGIN success %s' % username)
		self.cookies = resp.cookies
		return resp.cookies

	@staticmethod
	def comment_map(node, cookies, soup):
		cot = {}
		cot['comment_id'] = node['comment_id']
		cot['comment_uface'] = node.select('.WB_face img')[0]['src']
		cot['comment_uid'] = node.select('.WB_face img')[0]['usercard'][3:]
		cot['comment_text'] = Utils.get_innerhtml(node.select('.WB_text')[0])
		textstart = cot['comment_text'].find('：')
		cot['comment_text'] = cot['comment_text'][textstart + len('：'):]
		cot['comment_time'] = Utils.parse_time_text(node.select('.WB_from')[0].string)
		cot['comment_like'] = Utils.parse_num(node.select('.WB_handle span[node-type="like_status"] em')[0].string)
		return cot

	@staticmethod
	def get_page(htmls):
		soups = [BeautifulSoup(h, 'html.parser') for h in htmls]
		for s in soups:
			ps = s.select('a.page.S_txt1')
			if len(ps) > 0:
				return int(ps[0].text[1:2])
		return None

	@staticmethod
	def search_map_end(soup):
		if len(soup.select('.pl_noresult')) > 0:
			return True
		#if soup.select('a.page S_txt1')[0].text == u'第一页' 
		return False

	@staticmethod
	def search_map(node, cookies, soup):
		weibo_temp = Weibo()
		weibo_temp['mid'] = node['mid']
		usernode = node.select('img.W_face_radius')[0]
		uhref = node.select('.face a')[0]['href']
		weibo_temp['uid'] = uhref[uhref.rfind("/")+1:]
		WeiboUser.logger.debug('SEARCH_MAP uid %s mid %s' % (weibo_temp['uid'], weibo_temp['mid']))
		#weibo_temp['uid'] = usernode['usercard'][usernode['usercard'].find('id=') + 3:usernode['usercard'].find('&')]
		weibo_temp['uface'] = usernode['src']
		weibo_temp['nickname'] = usernode['alt']
		weibo_temp['text'] = Utils.get_innerhtml(node.select('p.comment_txt')[0])
		weibo_temp['time'] = Utils.parse_time(node.select('.WB_feed_detail a[node-type="feed_list_item_date"]')[0]['title']).isoformat()
		# some 'from' don't have rel="nofollow"
		if len(node.select('a[rel="nofollow"]')) > 0:
			weibo_temp['device'] = node.select('a[rel="nofollow"]')[0].string
		else:
			alltxt = Utils.get_text(node.select('.feed_from')[0]).strip()
			weibo_temp['device'] = alltxt[alltxt.find(u'来自') + 4:].strip()			
		forwardstr = node.select('a[action-type="feed_list_forward"] em')[0].string
		commentstr = node.select('a[action-type="feed_list_comment"] em')[0].string \
			if len(node.select('a[action-type="feed_list_comment"] em')) == 1 else ''
		weibo_temp['forward'] = Utils.parse_num(forwardstr)
		weibo_temp['comment'] = Utils.parse_num(commentstr)
		weibo_temp['like'] = Utils.parse_num(node.select('a[action-type="feed_list_like"] em')[0].string)
		
		# comments
		cindex = 1
		while True:
			(this_clist, end) = WeiboUser(cookies).get_comment(weibo_temp['mid'], cindex)
			if len(this_clist) > 0:
				weibo_temp['comment_list'].extend(this_clist)
				cindex += 1
			else:
				break
			if cindex > Utils.task['max_comment']:
				break
			Utils.sleep(15, 25)
		return weibo_temp

	@staticmethod
	def person_map(node, cookies, soup):
		weibo_temp = Weibo()
		# this weibo
		weibo_temp['mid'] = node['mid']
		weibo_temp['uid'] = Utils.get_uid_from_tfinfo(node['tbinfo'])
		WeiboUser.logger.debug('PERSON_MAP uid %s mid %s' % (weibo_temp['uid'], weibo_temp['mid']))
		weibo_temp['text'] = Utils.get_innerhtml(node.select('.WB_detail > .WB_text')[0])
		weibo_temp['time'] = Utils.parse_time(node.select('.WB_detail > .WB_from a[node-type="feed_list_item_date"]')[0]['title'])
		weibo_temp['device'] = node.select('.WB_detail > .WB_from a[rel="nofollow"]')[0].string
		weibo_temp['comment'] = Utils.parse_num(node.select('.WB_feed_handle ul span[node-type="comment_btn_text"]')[0].string)
		weibo_temp['forward'] = Utils.parse_num(node.select('.WB_feed_handle ul span[node-type="forward_btn_text"]')[0].string)
		weibo_temp['like'] = Utils.parse_num(node.select('.WB_feed_handle ul span[node-type="like_status"] em')[0].string)
		
		# comments
		cindex = 1
		while True:
			(this_clist, end) = WeiboUser(cookies).get_comment(weibo_temp['mid'], cindex)
			if len(this_clist) > 0:
				weibo_temp['comment_list'].extend(this_clist)
				cindex += 1
			else:
				break

		# inner weibo
		if(len(node.select('.WB_feed_expand')) > 0): 
			inner_wb = node.select('.WB_feed_expand')[0]
			weibo_temp['inner']['uid'] = inner_wb.select('.WB_info a[node-type="feed_list_originNick"]')[0]['usercard'][3:]
			weibo_temp['inner']['nickname'] = inner_wb.select('.WB_info a[node-type="feed_list_originNick"]')[0]['title']
			weibo_temp['inner']['text'] = Utils.get_innerhtml(inner_wb.select('.WB_text')[0])
			weibo_temp['inner']['mid'] = inner_wb.select('.WB_func .WB_handle')[0]['mid']
			for a in inner_wb.select('.WB_func .WB_handle ul a'):
				if a.has_key('suda-uatrack') and a['suda-uatrack'].find('transfer') != -1:
					weibo_temp['inner']['forward'] = Utils.parse_num(a.string)
				elif a.has_key('suda-uatrack') and a['suda-uatrack'].find('comment') != -1:
					weibo_temp['inner']['comment'] = Utils.parse_num(a.string)
			weibo_temp['inner']['time'] = Utils.parse_time(inner_wb.select('.WB_func .WB_from a[node-type="feed_list_item_date"]')[0]['title'])
			weibo_temp['inner']['device'] = inner_wb.select('.WB_func .WB_from a[rel="nofollow"]')[0].string
		return weibo_temp

	def get_comment(self, mid, page):
		wb_down = WeiboDonwloader(self.cookies)
		(html, pagenum, maxid) = wb_down.comment_page(mid = mid, page = page)
		return WeiboCssParser(html, self.cookies, '.list_ul > div[comment_id]', WeiboUser.comment_map).get_weibos()

	def get_tweet_by_userid(self, param_dict):
		wb_down = WeiboDonwloader(self.cookies)
		html = wb_down.person_page(uid = param_dict['uid'], page = param_dict['page'])
		return WeiboCssParser(html, self.cookies, param_dict['root_selector'], WeiboUser.person_map).get_weibos()

	def get_tweet_by_title(self, param_dict):
		wb_down = WeiboDonwloader(self.cookies)
		html = wb_down.search_page(title = param_dict['title'], page = param_dict['page'], \
				start = Utils.parse_input_date(param_dict['start']), end = Utils.parse_input_date(param_dict['end']))
		p = WeiboUser.get_page(html)
		self.logger.info('GET page %d, current page %s' % (param_dict['page'], str(p)))
		if p != None and p < param_dict['page']:
			return [], True
		return WeiboCssParser(html, self.cookies, param_dict['root_selector'], WeiboUser.search_map, WeiboUser.search_map_end).get_weibos()