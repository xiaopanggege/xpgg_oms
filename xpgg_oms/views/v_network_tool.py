#!/usr/bin/env python3
# -.- coding:utf-8 -.-

from django.shortcuts import render
from django.http import JsonResponse
from xpgg_oms.forms import *
from xpgg_oms.scripts import netscantool
import ast  # 去掉字符串的一层""

import logging
# Create your views here.
logger = logging.getLogger('xpgg_oms.views')

# 网络工具扫描
def net_tool(request):
    try:
        if request.method == 'GET':
            return render(request, 'network_tool/net_tool.html')
        elif request.method == 'POST':
            # 网段扫描
            if request.POST.get('scan_type') == 'ipscan':
                ipscan_ip = request.POST.get('ipscan_ip', None)
                try:
                    result_data = netscantool.ipscan(ipscan_ip)
                    response_data = {'result': result_data, 'status': True}
                    return JsonResponse(response_data)
                except Exception as e:
                    logger.error('无法获取IP网段扫描结果'+str(e))
                    return JsonResponse({'result': '无法获取IP网段扫描结果', 'status': False})
            # TCP端口扫描
            elif request.POST.get('scan_type') == 'portscan':
                portscan_ip = request.POST.get('portscan_ip', None)
                portscan_startport = ast.literal_eval(request.POST.get('portscan_startport', None))
                portscan_endport = ast.literal_eval(request.POST.get('portscan_endport', None))
                try:
                    result_data = netscantool.portscan(portscan_ip,portscan_startport,portscan_endport)

                    response_data = {'result': result_data, 'status': True}
                    return JsonResponse(response_data)
                except Exception as e:
                    logger.error('无法获取端口扫描结果'+str(e))
                    return JsonResponse({'result': '无法获取端口扫描结果', 'status': False})
            # 路由跟踪
            elif request.POST.get('scan_type') == 'traceroutescan':
                tracert_data = request.POST.get('tracert_data', None)
                try:
                    result_data = netscantool.traceroutescan(tracert_data)
                    response_data = {'result': result_data, 'status': True}
                    return JsonResponse(response_data)
                except Exception as e:
                    logger.error('无法获取路由跟踪结果'+str(e))
                    return JsonResponse({'result': '无法获取路由跟踪结果', 'status': False})

    except Exception as e:
        logger.error('网络扫描报错：', e)