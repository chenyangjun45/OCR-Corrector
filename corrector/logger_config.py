#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
__title__ = ''
__author__ = 'chenyj101'
__mtime__ = '2020/9/22'
# code is far away from bugs with the god animal protecting
    I love animals. They taste delicious.
              ┏┓      ┏┓
            ┏┛┻━━━┛┻┓
            ┃      ☃      ┃
            ┃  ┳┛  ┗┳  ┃
            ┃      ┻      ┃
            ┗━┓      ┏━┛
                ┃      ┗━━━┓
                ┃  神兽保佑    ┣┓
                ┃　永无BUG！   ┏┛
                ┗┓┓┏━┳┓┏┛
                  ┃┫┫  ┃┫┫
                  ┗┻┛  ┗┻┛
"""

import logging
import time
import os

base_logger = logging.getLogger("tk_logger")
base_logger.setLevel(logging.DEBUG)

curdir = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')

now_date = time.strftime("%Y_%m_%d")
fh = logging.FileHandler(curdir + '/logs/%s' % (now_date+'_dl.log'))

# 再创建一个handler，用于输出到控制台
# ch = logging.StreamHandler()

# 定义handler的输出格式formatter
formatter = logging.Formatter(
	"%(asctime)s %(pathname)s %(filename)s %(funcName)s %(lineno)s "
	"%(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S"
)
fh.setFormatter(formatter)
# ch.setFormatter(formatter)

base_logger.addHandler(fh)
# base_logger.addHandler(ch)
