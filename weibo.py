#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy
import json
from datetime import *
from utils import CJsonEncoder

class Weibo: 
    weibo_temp = {
        'uid': None,
        'nickname': None,
        'uface': None,
        'mid': None,
        'text': None,
        'time': None,
        'device': None, 
        'forward': None,
        'comment': None,
        'like': None,
        'comment_list': [],
        'inner': {}
    }

    def __init__(self): 
        self.__wb = copy.deepcopy(Weibo.weibo_temp)

    def __getitem__(self, key): 
        return self.__wb[key] 
    def __setitem__(self, key, value): 
        self.__wb[key] = value
    
    def __str__(self):
        return json.dumps(self.__wb, indent = True, cls = CJsonEncoder, ensure_ascii=False)