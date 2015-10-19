#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy
from bs4 import BeautifulSoup

class WeiboCssParser:
    def __init__(self, htmls, cookies, root_selector, map_func, is_end=None):
        self.end = False
        self.root_selector = root_selector
        self.cookies = cookies
        self.map_func = map_func
        self.soups = [BeautifulSoup(html, 'html.parser') for html in htmls]
        self.weibo_nodes = []
        for soup in self.soups:
            if hasattr(is_end ,'__call__') and is_end(soup):
                self.end = True
            else:
                self.weibo_nodes.append((soup.select(root_selector), soup))
        self.weibos = []
        for s in self.weibo_nodes:
            self.weibos.extend([map_func(n, cookies, s[1]) for n in s[0]])

    def get_weibos(self):
        return self.weibos, self.end, 