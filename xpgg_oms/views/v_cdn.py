#!/usr/bin/env python3
# -.- coding:utf-8 -.-

from django.shortcuts import render
from django.http import JsonResponse
from xpgg_oms.forms import *
from xpgg_oms.models import *
from .v_general import getPage

import logging
# Create your views here.
logger = logging.getLogger('xpgg_oms.views')


# 华为CDN,ajax处理也直接写一起
def huawei_cdn(request):
    if request.method == 'GET':
        history = request.GET.get('history')
        cdn_data = HuaweiCdnInfo.objects.all().order_by('-id')
        data_list = getPage(request, cdn_data, 10)
        return render(request, 'cdn/huawei_cdn.html', {'data_list':data_list, 'history':history})
    result = {'result': None, 'status': False}
    try:
        if request.is_ajax():
            if request.POST.get('huawei_cdn_tag_key') == 'cdn_refresh':
                select_type = request.POST.get('select_type', 'file')
                urls = re.split('\n|;', request.POST.get('urls'))
                for url in urls:
                    if select_type == 'file':
                        if not re.match(r'https?://', url):
                            result['result'] = 'urls格式有误'
                            return JsonResponse(result)
                    elif select_type == 'directory':
                        if not re.match(r'https?://.+/$', url):
                            result['result'] = 'urls格式有误'
                            return JsonResponse(result)
                    else:
                        result['result'] = '类型不符'
                        return JsonResponse(result)
                from xpgg_oms.scripts import huawei_cdn_manage
                response_data = huawei_cdn_manage.refresh_cdn(select_type,urls)
                if response_data['status']:
                    try:
                        urls_list = []
                        for url in urls:
                            urls_list.append({'url': url, 'status': '执行中'})
                        HuaweiCdnInfo.objects.create(task_id=response_data['result']['id'], task_type='缓存刷新',
                                                    task_status=response_data['result']['status'], urls=urls_list,
                                                     operator=request.user.username)
                        result['status'] = True
                        result['result'] = '刷新缓存任务提交成功'
                    except Exception as e:
                        result['result'] = '刷新缓存任务提交成功，但插入数据库出错' + str(e)
                else:
                    result['result'] = response_data['result']
                return JsonResponse(result)
            elif request.POST.get('huawei_cdn_tag_key') == 'cdn_preheating':
                urls = re.split('\n|;', request.POST.get('urls'))
                for url in urls:
                    if not re.match(r'https?://', url):
                        result['result'] = 'urls格式有误'
                        return JsonResponse(result)
                from xpgg_oms.scripts import huawei_cdn_manage
                response_data = huawei_cdn_manage.preheating_cdn(urls)
                if response_data['status']:
                    try:
                        urls_list = []
                        for url in urls:
                            urls_list.append({'url': url, 'status': '执行中'})
                        HuaweiCdnInfo.objects.create(task_id=response_data['result']['id'], task_type='缓存预热',
                                                    task_status=response_data['result']['status'], urls=urls_list,
                                                     operator=request.user.username)
                        result['status'] = True
                        result['result'] = '缓存预热任务提交成功'
                    except Exception as e:
                        result['result'] = '缓存预热任务提交成功，但插入数据库出错' + str(e)
                else:
                    result['result'] = response_data['result']
                return JsonResponse(result)
            elif request.POST.get('huawei_cdn_tag_key') == 'history_update':
                task_id = request.POST.get('task_id')
                from xpgg_oms.scripts import huawei_cdn_manage
                response_data = huawei_cdn_manage.history_task(task_id)
                if response_data['status']:
                    try:
                        HuaweiCdnInfo.objects.filter(task_id=task_id).update(urls=response_data['result']['urls'],
                                                                             task_status=response_data['result']['status'])
                        result['result'] = response_data['result']
                        result['status'] = True
                        return JsonResponse(result)
                    except Exception as e:
                        result['result'] = '刷新任务提交成功，但更新数据库出错' + str(e)
                else:
                    result['result'] = response_data['result']
                return JsonResponse(result)
            else:
                result['result'] = '华为CDN,ajax提交了错误的tag'
                return JsonResponse(result)
    except Exception as e:
        logger.error('华为CDN,ajax提交处理有问题', e)
        result['result'] = '华为CDN,ajax提交处理有问题'
        return JsonResponse(result)