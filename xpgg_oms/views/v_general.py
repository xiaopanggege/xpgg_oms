#!/usr/bin/env python3
# -.- coding:utf-8 -.-

from django.conf import settings

from django.core.paginator import Paginator
import logging
# Create your views here.
logger = logging.getLogger('xpgg_oms.views')


def global_setting(request):
    return {
            'SITE_NAME': settings.SITE_NAME,
            'SITE_DESC': settings.SITE_DESC,
            'SITE_URL': settings.SITE_URL}


# 分页代码，第一个参数要request是因为里头代码要request.GET东西需要有request支持
def getPage(request, data_list, page_num=10):
    # 传2参数，一个是要分页的列表或者queryset，一个是每页显示数量默认10
    paginator = Paginator(data_list, page_num)  # import引入的django自带分页模块Paginator，data_list是数据库查询后的queryset，每页10条记录
    try:
        page = int(request.GET.get('page', 1))  # 从页面上的?page获取值，看html里分页设置了这个值,如果没有就赋值1，第一页
        data_list = paginator.page(page)
    except Exception:
        data_list = paginator.page(1)
    return data_list
