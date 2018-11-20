#!/usr/bin/env python3
# -.- coding:utf-8 -.-

from xpgg_oms.models import *
import logging
# Create your views here.
logger = logging.getLogger('xpgg_oms.views')


from rest_framework.pagination import PageNumberPagination
from rest_framework import viewsets
from rest_framework import mixins
from xpgg_oms.serializers import AppReleaseListSerializer


class StandardPagination(PageNumberPagination):
    # 每页显示个数
    page_size = 1
    # url中默认修改每页个数的参数名
    # 比如http://127.0.0.1:8000/api/snippets/?page=1&page_size=4
    # 就是显示第一页并且显示个数是4个
    page_size_query_param = 'page_size'
    page_query_param = "page"
    # 每页最大个数不超过100
    max_page_size = 100


class AppReleaseListViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
        list:
            列表显示
    """

    queryset = AppRelease.objects.all()
    serializer_class = AppReleaseListSerializer
    pagination_class = StandardPagination