# 下面这个写法兼容1.10和之前版本的中间件，是这样的之前1.9和一下版本中间件不需要继承来实现
# 所以中间件不用继承自任何类（可以继承 object ）也不用import任何东西（除了你代码需要的），
# 而1.10开始需要继承MiddlewareMixin，另外就是逻辑上面也有一点区别，1.9以前正常中间件的执行
# 过程是先执行所有中间件的request然后执行views.py里的函数然后依次从最后一个中间件的reponse向上执行（省略中间件的
# view和except比较少用到 ），假设当执行到第二个中间件出错的时候，则会从最后一个中间件的reponse开始
# 依次向上返回，而1.10开始则是从出错的第二个中间件开始向上返回

try:
    from django.utils.deprecation import MiddlewareMixin  # Django 1.10.x
except ImportError:
    MiddlewareMixin = object  # Django 1.4.x - Django 1.9.x

from django.shortcuts import render, HttpResponse, redirect, HttpResponseRedirect
from django.http import JsonResponse
from django.conf import settings
import logging
# Create your views here.
logger = logging.getLogger('xpgg_oms.views')


# 用户是否登陆判断，如果没就跳转到登陆页
class UserAuthentication(MiddlewareMixin):
    def process_request(self, request):
        if not request.user.is_authenticated:
            if request.path != '/login/':
                # if request.is_ajac
                # return HttpResponseRedirect('/login/')
                return HttpResponseRedirect('%s?next=%s' % (settings.LOGIN_URL, request.path))

    # process_reponse这里没用上，忽略即可
    def process_reponse(self, reponse):
        pass