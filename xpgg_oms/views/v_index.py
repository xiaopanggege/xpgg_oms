#!/usr/bin/env python3
# -.- coding:utf-8 -.-

from django.shortcuts import render
from django.http import JsonResponse
from xpgg_oms.forms import *
from xpgg_oms.models import *

import logging
# Create your views here.
logger = logging.getLogger('xpgg_oms.views')

# 首页仪表盘
def index(request):
    return render(request, 'index.html', locals())


# 首页仪表盘ajax
def index_ajax(request):
    result = {'result': None, 'status': False}
    app_log = []
    try:
        if request.is_ajax():
            # 在ajax提交时候多一个字段作为标识，来区分多个ajax提交哈，厉害！
            if request.GET.get('index_tag_key') == 'index_get_data':
                result['result'] = {}
                result['result']['server_list_count'] = ServerList.objects.all().count()
                result['result']['network_list_count'] = NetworkList.objects.all().count()
                result['result']['physical_pc_count'] = ServerList.objects.filter(server_type='0').count()
                result['result']['virtual_machine_count'] = ServerList.objects.filter(server_type='1').count()
                result['result']['sys_type_windows_count'] = ServerList.objects.filter(sys_type='windows').count()
                result['result']['sys_type_linux_count'] = ServerList.objects.filter(sys_type='linux').count()
                result['result']['saltkey_accepted_count'] = SaltKeyList.objects.filter(certification_status='accepted').count()
                result['result']['saltkey_denied_count'] = SaltKeyList.objects.filter(certification_status='denied').count()
                result['result']['saltkey_rejected_count'] = SaltKeyList.objects.filter(certification_status='rejected').count()
                result['result']['saltkey_unaccepted_count'] = SaltKeyList.objects.filter(certification_status='unaccepted').count()
                result['result']['minion_up_count'] = MinionList.objects.filter(minion_status='在线').count()
                result['result']['minion_down_count'] = MinionList.objects.filter(minion_status='离线').count()
                result['result']['minion_error_count'] = MinionList.objects.filter(minion_status='异常').count()
                result['result']['minion_windows_count'] = MinionList.objects.filter(sys='Windows').count()
                result['result']['minion_linux_count'] = MinionList.objects.filter(sys='Linux').count()
                result['status'] = True
                # 返回字典之外的需要把参数safe改成false如：JsonResponse([1, 2, 3], safe=False)
                return JsonResponse(result)
            else:
                result['result'] = '仪表盘ajax提交了错误的tag'
                return JsonResponse(result)
    except Exception as e:
        logger.error('仪表盘ajax提交处理有问题', e)
        result['result'] = '仪表盘ajax提交处理有问题'
        return JsonResponse(result)