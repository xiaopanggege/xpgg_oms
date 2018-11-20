#!/usr/bin/env python3
# -.- coding:utf-8 -.-

from django.shortcuts import render, redirect
from django.http import JsonResponse  # 1.7以后版本json数据返回方法
from xpgg_oms.forms import *
from django.conf import settings
from django.contrib.auth import logout, login, authenticate  # 登陆注销注册django自带模块引用
from django.contrib.auth.hashers import make_password  # django自带密码加密模块


import logging
# Create your views here.
logger = logging.getLogger('xpgg_oms.views')


# 登录页
def do_login(request):
    try:
        if request.method == 'GET':
            return render(request, 'login.html')
        elif request.is_ajax():
            username = request.POST.get('username')
            password = request.POST.get('password')
            next_url = request.POST.get('next')
            user = authenticate(username=username, password=password)  # 调用django自带验证模块key是Myuser的
            if user is not None and user.is_active:  # user如果验证成功返回user对象失败返回None，is_active是判断用户是否激活状态的，自带的用户注册默认状态是true激活
                login(request, user)
                if next_url:
                    return JsonResponse({'result': next_url, 'status': True})

                else:
                    return JsonResponse({'result': '/', 'status': True})
            else:
                return JsonResponse({'status': False})
    except Exception as e:
        logger.error(e)
        return render(request, 'login.html')


# 退出
def do_logout(request):
    try:
        logout(request)
    except Exception as e:
        logger.error(e)
    return redirect(settings.LOGIN_URL)#返回到登录页
