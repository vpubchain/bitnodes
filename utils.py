#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# utils.py - Common helper methods.
#
# Copyright (c) Addy Yeow Chin Heng <ayeowch@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Common helper methods.
"""

import os
import redis
from ipaddress import ip_network
import smtplib
from email.mime.text import MIMEText


#邮件服务器地址及发送邮件账户和密码
MAIL_FROM='280507775@qq.com'
SMTP_SERVER='smtp.qq.com'
EMAIL_USER='280507775@qq.com'
EMAIL_PASSWD='huuepttziehlbghe'

#对应服务器的邮件接收人,多个的话再考虑为数组
MAILS ='280507775@qq.com'

def sendwainingmail(body):
    msg = MIMEText(body)
    msg['Subject'] = '监管平台系统告警'
    msg['From'] = MAIL_FROM
    msg['To'] = MAILS

    #发送邮件
    server=smtplib.SMTP(SMTP_SERVER)
    server.login(EMAIL_USER,EMAIL_PASSWD)
    server.sendmail(MAIL_FROM, MAILS, msg.as_string())
    server.quit()

def new_redis_conn(db=0):
    """
    Returns new instance of Redis connection with the right db selected.
    """
    #socket = os.environ.get('REDIS_SOCKET', "/tmp/redis.sock")
    socket = os.environ.get('REDIS_SOCKET', "/var/run/redis/redis.sock")
    password = os.environ.get('REDIS_PASSWORD', None)
    return redis.StrictRedis(db=db, password=password, unix_socket_path=socket)


def get_keys(redis_conn, pattern, count=500):
    """
    Returns Redis keys matching pattern by iterating the keys space.
    """
    keys = []
    cursor = 0
    while True:
        try:
            (cursor, partial_keys) = redis_conn.scan(cursor, pattern, count)
        except:
            sendwainingmail("redis异常！，请检查！")
            break
         
        keys.extend(partial_keys)
        if cursor == 0:
            break
    return keys


def ip_to_network(address, prefix):
    """
    Returns CIDR notation to represent the address and its prefix.
    """
    network = ip_network(unicode("{}/{}".format(address, prefix)),
                         strict=False)
    return "{}/{}".format(network.network_address, prefix)
