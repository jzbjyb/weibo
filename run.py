#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import logging
import json
import time
import random
import copy
import os

from page_downloader import WeiboDonwloader
from weibo_parser import WeiboCssParser
from weibo_user import WeiboUser
from weibo import Weibo
from utils import Utils, jsonS

# reload encoding as utf-8
reload(sys)
sys.setdefaultencoding("utf-8")

LEVEL_MAP = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'error': logging.ERROR,
    'warn': logging.WARN
}

def login(us):
    result = {}
    for u in us:
        user = WeiboUser()
        user.wblogin(u['username'], u['passwd'])
        result[u['username']] = user
    return result

def loop_page(start, end, task):
    page_trunc = 3
    def get_file_suf(start, num):
        return '.' + str(start) + '-' + str(start + num -1)

    def rand_user(us):
        rd = random.randint(0, len(us) - 1)
        root_logger.info('USER %s' % us[rd]['username'])
        return [us[rd]['username'], us[rd]['passwd']]

    
    base_filename = Utils.getfilename(task['output'], task['user_func_param'])
    filename = base_filename + get_file_suf(start, page_trunc)
    root_logger.info('OUTPUT FILE ' + filename)
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))
    opfile = open(filename, 'w+')

    if end == None:
        end = sys.maxint
    
    user = task['user_map'][rand_user(task['users'])[0]]
    pages = 0

    try:
        while start <= end:
            # page_trunc page per user
            if pages >= page_trunc:
                pages = 0
                user = task['user_map'][rand_user(task['users'])[0]]
                opfile.close()
                filename = base_filename + get_file_suf(start, page_trunc)
                root_logger.info('OUTPUT FILE ' + filename)
                if not os.path.exists(os.path.dirname(filename)):
                    os.makedirs(os.path.dirname(filename))
                opfile = open(filename, 'w+')

            task['user_func_param']['page'] = start
            (wbl, isend) = eval('user.' + task['user_func'])(task['user_func_param'])
            pages += 1
            
            if isend:
                root_logger.info('ALL PAGE DONE')
                break
            elif len(wbl) > 0:
                if pages > 1:
                    opfile.write(',\n')
                opfile.write(',\n'.join([str(wb) for wb in wbl]))
            if start < end:
                sl = [int(s) for s in task['sleep'].split('-')]
                Utils.sleep(sl[0], sl[1])
            
            start += 1
    except:
        root_logger.exception('RUN EXCEPTION page %s' % start)
    finally:
        opfile.close()


def loop_task(task):
    if len(task['for'].items()) == 0:
        if task['page_range'] == 'all':
            loop_page(1, None, task)
        elif isinstance(task['page_range'], str) and task['page_range'].find('-') != -1:
            p = [int(ps) for ps in filter(Utils.filter_empty, task['page_range'].split('-'))]
            if len(p) == 2:
                loop_page(p[0], p[1], task)
            elif len(p) == 1:
                loop_page(p[0], None, task)
        else:
            loop_page(task['page_range'], task)
        return
    cur = task['for'].items()[0]
    child_task = copy.deepcopy(task)
    del child_task['for'][cur[0]]
    for v in cur[1]:
        child_task['user_func_param'][cur[0]] = v
        loop_task(child_task)


if __name__ == '__main__':
    
    # init task
    if len(sys.argv) > 1:
        task = jsonS.load(file(sys.argv[1]))
    else:
        task = jsonS.load(file('task.txt'))
    task['level'] = 'debug' if not task.has_key('level') else task['level']
    Utils.task = task


    # overall log config
    Level = LEVEL_MAP[task['level']]
    root_logger = logging.getLogger('weibo')
    root_logger.setLevel(Level)
      
    # handler for file 
    fh = logging.FileHandler('weibo.log')
    fh.setLevel(Level)  
      
    # handler for console
    ch = logging.StreamHandler()
    ch.setLevel(Level)  
      
    # handler output format  
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')  
    fh.setFormatter(formatter)  
    ch.setFormatter(formatter)
      
    root_logger.addHandler(fh)
    root_logger.addHandler(ch)

    task['user_map'] = login(task['users'])
    loop_task(task)    