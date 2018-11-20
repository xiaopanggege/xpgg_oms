#!/usr/bin/env python3
# -.- coding:utf-8 -.-

from django.shortcuts import render
import json
from django.http import JsonResponse, HttpResponseRedirect
import time
from xpgg_oms.forms import *
from xpgg_oms.models import *
from xpgg_oms import cron
from xpgg_oms.salt_api import SaltAPI
from django.conf import settings
import requests
# 下面这个是py3解决requests请求https误报问题
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from .v_general import getPage

import logging
# Create your views here.
logger = logging.getLogger('xpgg_oms.views')


# salt执行state.sls的返回结果格式化，因为通过api返回的结果不怎么好看呵呵
def format_state(result):
    a = result
    # b是返回minion列表
    b = (a['return'])
    # 用来存放所有minion格式化后的结果的
    result_data = []
    try:
        # i是return后面的列表其实就是a['return'][0]
        for i in b:
            # key是minion的ID,value是这个ID执行的所有结果又是一个字典
            for key, value in i.items():
                succeeded = 0
                failed = 0
                changed = 0
                Total_states_run = 0
                Total_run_time = 0
                minion_id = key
                run_num = len(value)  # 得到执行的state个数
                result_list = [k for k in range(run_num)] #把列表先用数字撑大，因为接收的数据随机的顺序如（3,5,6），先撑开列表到时候假设是3过来就插3的位子这样顺序就有序了
                for key1, value1 in value.items():
                    # print(value1)
                    # key1是一个个state的ID，value1是每个state的结果
                    key1 = key1.split('_|-')
                    Function = key1[0] + '_' + key1[-1]
                    ID = key1[1]
                    Name = key1[2]
                    aaa = '----------\n' + 'ID: '.rjust(14) + ID + '\n' + 'Function: '.rjust(
                        14) + Function + '\n' + 'Name: '.rjust(14) + Name + '\n' + 'Result: '.rjust(14) + str(
                        value1['result']) + '\n' + 'Comment: '.rjust(14) + value1['comment'] + '\n'
                    # start_time有的没有有的有
                    if value1.get('start_time'):
                        aaa += 'Started: '.rjust(14) + str(value1['start_time']) + '\n'
                    # duration有的没有有的有
                    if value1.get('duration'):
                        aaa += 'Duration: '.rjust(14) + str(value1['duration']) + ' ms' + '\n'
                        Total_run_time += value1['duration']
                    # changes都有，就算没值也是一个空的{}
                    if value1['changes'] == {}:
                        aaa += 'Changes: '.rjust(14)+'\n'
                    elif type(value1['changes']) == str:
                        aaa += 'ChangesIs: '.rjust(14) + '\n' + ''.rjust(14) + '----------\n'
                        aaa += ''.rjust(14) + value1['changes'] + ':\n' + ''.rjust(18) + '----------\n'
                    else:
                        aaa += 'ChangesIs: '.rjust(14) + '\n' + ''.rjust(14) + '----------\n'
                        for key in value1['changes'].keys():

                            if type(value1['changes'][key]) == dict:
                                aaa += ''.rjust(14) + key + ':\n' + ''.rjust(18) + '----------\n'
                                for ckey, cvalue in value1['changes'][key].items():
                                    aaa += ''.rjust(18) + ckey + ':\n' + ''.rjust(22) + str(cvalue).replace('\n','\n'+' '*18) + '\n'
                            else:
                                aaa += ''.rjust(14) + key + ':\n' + ''.rjust(18) + str(value1['changes'][key]).replace('\n','\n'+' '*18) + '\n'
                        changed += 1
                    if value1.get('__run_num__') is None:
                        result_list.append(aaa)
                    else:
                        result_list[value1.get('__run_num__')] = aaa
                    if value1['result']:
                        succeeded += 1
                    else:
                        failed += 1
                    Total_states_run += 1
                Total_run_time = Total_run_time / 1000
                bbb =74*'-'+ '\nSummary for %s\n-------------\nSucceeded: %d (changed=%d)\nFailed:    %2d\n-------------\nTotal states run:     %d\nTotal run time:    %.3f s\n\n' % (
                minion_id, succeeded, changed, failed, Total_states_run, Total_run_time)
                result_list.insert(0, bbb)
                result_data.extend(result_list)
        return result_data
    #如果格式化有问题，就把原来的以str来返回，然后在调用这个格式化的方法里写判断如果为str说明格式化失败，然后该怎么处理就怎么处理呵呵
    except Exception as e:
        logger.error('格式化不成功'+str(e))
        return str(a)


# 新的模块部署方法，采用了异步，并且加强了逻辑判断，加强了容错率，后期准备再加入入库用来做salt任务管理使用
def module_deploy(request):
    if request.method == 'GET':
        return render(request, 'saltstack/module_deploy.html')
    elif request.is_ajax() and request.POST.get('module_deploy_tag_key') == 'state_exe':
        # 这里没有做对传入tgt判断是否存在并且是否离线，自己给自己埋坑了因为可以支持多种tgt_type判断太麻烦了蛋疼，不过下面有通过async_state_api返回值判断！！！！！！！！！！！！！！！
        data_list = []  # 用来存结果的
        try:
            tgt = request.POST.get('tgt', None)
            tgt_type = request.POST.get('tgt_type')
            arg = request.POST.getlist('arg')
            # 下面这个是执行state用队列模式，还有一种是可以用并行，用队列安全性高一些不会出现同时执行同一个state对同一台minion但是相应速度慢
            # 并且我发现如果在下面api接口async_state_api里直接写arg=arg.append('queue=True')是不行的奶奶的，弄半天才发现！
            arg.append('queue=True')
            with requests.Session() as s:
                saltapi = SaltAPI(session=s)
                # 当调用api失败的时候比如salt-api服务stop了会返回false
                if saltapi.get_token() is False:
                    response_data = '模块部署失败，SaltAPI调用get_token请求出错'
                    return JsonResponse({'result': response_data, 'status': False})
                else:
                    # 调用async_state_api方法来执行部署
                    jid = saltapi.async_state_api(tgt=tgt, tgt_type=tgt_type, arg=arg)
                    # 当调用api失败的时候比如salt-api服务stop了会返回false
                    if jid is False:
                        response_data = '模块部署失败，SaltAPI调用async_state_api请求出错'
                        return JsonResponse({'result': response_data, 'status': False})
                    # 判断jid如果返回值如果为[{}]表明没有这个minion，我会在后期保证不出现这种现象也就不需要这个判断了，从源头解决！
                    elif jid['return'] == [{}]:
                        response_data = '模块部署失败，请确认minion是否存在。。'
                        return JsonResponse({'result': response_data, 'status': False})
                    else:
                        jid = jid['return'][0]['jid']
                        check_count = 60
                        re_count = 0
                        time.sleep(15)
                        while check_count:
                            false_count = 0
                            job_status = saltapi.job_active_api(tgt=tgt, tgt_type=tgt_type, arg=jid)
                            if job_status is False:
                                response_data = '模块部署失败，SaltAPI调用job_active_api请求出错'
                                return JsonResponse({'result': response_data, 'status': False})
                            else:
                                # 获取minion的数量用来给下面做对比使用
                                minion_count = len(job_status['return'][0].items())

                                '''这步是因为结果是一个字典套字典，如：{'return': [{'192.168.68.51': {'fun': 'cmd.script', 'arg': ['salt://script/test.py'],
                                'tgt_type': 'glob', 'user': 'saltapi', 'pid': 3015, 'jid': '20170807144951631265', 'ret': '', 'tgt': '192.168.68.51'},
                                '192.168.68.50-master': {}}]}里面有2个minion'''
                                for key, value in job_status['return'][0].items():
                                    # !!使用job_active_api方法检测任务状态，如果有值说明还在运行，如果值为{}即空说明运行结束或为False表示minion离线，这步经典想了好久！！
                                    # 因为如果直接判断为空或者为False没想过如何确认全部都是为空，最后终于想到反着判断哈哈
                                    if value:
                                        # 为真说明job还在执行，刚好用来恢复断线false的计数器
                                        if re_count > 0:
                                            re_count = 0
                                        # 如果为真说明还没运行结束，break跳出不会运行下面的else，则jid_data为空，然后跳到计数-1再睡眠30秒继续下一轮
                                        break
                                    # 这个留在这里做个说明，我发现在调用job_active_api接口的时候经常失败返回false了，感觉是接口有问题
                                    # 而如果出现都是false用jid_api接口取到的结果就会是[{}]所以下面对这个要做一层判断，以免因为接口不稳导致没取到结果
                                    # 另外注意这里value is False看上去好像和上面是if value是相反的可以直接用else代替，但是不行！因为当执行完毕返回是{}而{}和False是不同的！
                                    if value is False:
                                        # 一次falst就计数器+1直到等于你执行任务的minion的数量，说明特么全断线了
                                        false_count += 1
                                        # 如果全部是minion（假设你是批量部署）都false并且连续监测2次都是那就不用跑了直接返回离线结束呵呵
                                        if false_count == minion_count and re_count == 2:
                                            response_data = {'result': '对不起您要部署的所有minion都离线了',
                                                             'status': False}
                                            return JsonResponse(response_data)
                                        # re计数器不到3次则+1，继续下一轮循环
                                        elif false_count == minion_count:
                                            # print('全fasle出现了', re_count)
                                            re_count += 1
                                            break

                                # 当上面的for正常执行结束没有因为break退出时候说明job执行完毕了(或者是有部分执行完毕有部分返回了false)，则执行下面
                                else:
                                    jid_data = saltapi.jid_api(jid=jid)
                                    # 注意[{}] ！= False所以不能用if jid_data['return']判断是否有数据，这个坑埋了好久奶奶的！！！
                                    if jid_data is False:
                                        response_data = '模块部署失败，SaltAPI调用jid_api请求出错'
                                        return JsonResponse({'result': response_data, 'status': False})
                                    elif jid_data['return'] == [{}]:
                                        # 这个判断没必要，只是留这里做个说明，我之前上面没有做if value is False判断的时候，如果job_active_api
                                        # 的结果全部false了也会正常跳出for循环，然后在这里会出现jid_data['return'] == [{}]的情况，因为false
                                        # 说明minion断线了，结果肯定取到空了；还有另一种情况就是还没有返回值的时候也会等于[{}],
                                        # 不过后面我在上面加了对false做判断这里就没必要了呵呵
                                        pass
                                    else:
                                        format_result = format_state(jid_data)
                                        # 这个是对格式化输出的一个判断，类型str说明格式化出错了呵呵，一般在minion一个sls未执行完成又执行会出现
                                        if type(format_result) == str:
                                            data_list.append(format_state(jid_data))
                                            response_data = {'result': jid_data['return'][0], 'status': False}
                                            return JsonResponse(response_data)
                                        else:
                                            data_list.extend(format_state(jid_data))
                                            break
                                check_count -= 1
                                time.sleep(10)
                        else:
                            response_data = {
                                'result': '执行时间已经超过10分钟了，建议您可以去salt命令执行里有任务查看快捷通道，jid：%s 的结果以免耽误泡妞时间。。' % jid,
                                'status': False}
                            return JsonResponse(response_data)
        except Exception as e:
            response_data = {'result': '模块部署失败，内部代码可能有问题：%s。。' % str(e), 'status': False}
            return JsonResponse(response_data)
        response_data = {'result': data_list, 'status': True}
        return JsonResponse(response_data)  # 新版1.7以上写法


# salt-ssh运行state的输出格式化，和salt运行state差不多，有时间可以试着整合
def ssh_format_state(result):
    a = result
    succeeded = 0
    failed = 0
    changed = 0
    Total_states_run = 0
    Total_run_time = 0
    # b是返回minion列表
    b = a['return']
    try:
        for i in b:
            for key, value in i.items():
                minion_id = key
                run_num = len(value['return'])  # 得到执行的state个数,就是这里和salt格式化不同
                result_list = [k for k in range(run_num)]  # 把列表先用数字撑大，因为接收的数据随机的顺序如（3,5,6），先撑开列表到时候假设是3过来就插3的位子这样顺序就有序了
                for key1, value1 in value['return'].items():
                    # print(value1)
                    # key1是一个个state的ID，value1是每个state的结果
                    key1 = key1.split('_|-')
                    Function = key1[0] + '_' + key1[-1]
                    ID = key1[1]
                    Name = key1[2]
                    aaa = '----------\n' + 'ID: '.rjust(14) + ID + '\n' + 'Function: '.rjust(
                        14) + Function + '\n' + 'Name: '.rjust(14) + Name + '\n' + 'Result: '.rjust(14) + str(
                        value1['result']) + '\n' + 'Comment: '.rjust(14) + value1['comment'] + '\n'
                    # start_time有的没有有的有
                    if value1.get('start_time'):
                        aaa += 'Started: '.rjust(14) + str(value1['start_time']) + '\n'
                    # duration有的没有有的有
                    if value1.get('duration'):
                        aaa += 'Duration: '.rjust(14) + str(value1['duration']) + ' ms' + '\n'
                        Total_run_time += value1['duration']
                    # changes都有，就算没值也是一个空的{}
                    # print(value1['changes'])
                    if value1['changes'] == {}:
                        aaa += 'Changes: '.rjust(14) + '\n'
                    else:
                        #这里用ChangesIs而不是Changes是为了前端区分方便改颜色哈哈
                        aaa += 'ChangesIs: '.rjust(14) + '\n' + ''.rjust(14) + '----------\n'
                        for key in value1['changes'].keys():

                            if type(value1['changes'][key]) == dict:
                                aaa += ''.rjust(14) + key + ':\n' + ''.rjust(18) + '----------\n'
                                # print(value1['changes'][key])
                                # aaa+=''.rjust(14) + key + ':\n'+ ''.rjust(18) + str(value1['changes'][key]) + '\n'+ '\n' + ''.rjust(14) + '----------\n'
                                # aaa +=''.rjust(18) + '----------\n' + ''.rjust(18) + '----------\n'
                                for ckey, cvalue in value1['changes'][key].items():
                                    aaa += ''.rjust(18) + ckey + ':\n' + ''.rjust(22) + str(cvalue).replace('\n',
                                                                                                            '\n' + ' ' * 18) + '\n'
                                    # aaa+=''.rjust(14) + ckey + ':\n'+ ''.rjust(18) + str(value1['changes'][key][ckey]) + '\n'
                            else:
                                aaa += ''.rjust(14) + key + ':\n' + ''.rjust(18) + str(value1['changes'][key]).replace('\n',
                                                                                                                       '\n' + ' ' * 18) + '\n'
                        changed += 1
                    result_list[value1['__run_num__']] = aaa
                    if value1['result']:
                        succeeded += 1
                    else:
                        failed += 1
                    Total_states_run += 1
                Total_run_time = Total_run_time / 1000
                bbb = 74 * '-' + '\nSummary for %s\n-------------\nSucceeded: %d (changed=%d)\nFailed:    %2d\n-------------\nTotal states run:     %d\nTotal run time:    %.3f s\n\n' % (
                    minion_id, succeeded, changed, failed, Total_states_run, Total_run_time)
                result_list.insert(0, bbb)
                return result_list
                # 如果格式化有问题，就把原来的以str来返回，然后在调用这个格式化的方法里写判断如果为str说明格式化失败，然后该怎么处理就怎么处理呵呵
    except Exception as e:
        logger.error('格式化不成功' + str(e))
        return str(a)


# minion客户端salt-ssh部署
def minion_client_install(request):
    try:
        if request.method == 'GET':
            return render(request, 'saltstack/minion_client_install.html')
        else:
            server_ip = request.POST.get('server_ip')
            server_username = request.POST.get('server_username')
            server_password = request.POST.get('server_password')
            # 我在前端设置了如果没输入minion_id则会返回''空，不过这个还是会被django的get收到只是变成minion_id=''还是存在minion_id的
            # 所以我在后端的sls文件里加了判断如果为''的判断
            minion_id = request.POST.get('minion_id')
            if request.POST.get('master'):
                master = request.POST.get('master')
            else:
                master = settings.SITE_SALT_MASTER_IP
            server_port = request.POST.get('server_port')
            try:
                # 直接打开耦合性就比较差了，我这为了方便，其实最好是用salt的cmd.run来打开写入比较正规，而且低耦合
                with open(r'/etc/salt/roster','w') as roster:
                    # 本来我是没打算用覆盖写入的方式，后来想想如果不用覆盖写入判断起来更耗性能，所以干脆简单点改成覆盖了
                    roster.write('\n%s:\n  host: %s\n  user: %s\n  passwd: %s\n  port: %s\n' % (server_ip, server_ip, server_username, server_password, server_port))
                print('主机信息写入成功')
            except Exception as e:
                print('写入主机信息失败')
                return JsonResponse({'result': '写入主机信息失败', 'status': False})
            else:
                data = {'client': 'ssh',
                        'tgt': server_ip,
                        'fun': 'test.ping'
                        }
                try:
                    rpost = requests.post('%s/run' % settings.SITE_SALT_API_URL, json=data)
                    rpost.raise_for_status()
                    #这里要注意！！！！！，这步测试客户机连通性基本100%不会报错，因为报错也会返回错误结果，所以这里的try是
                    #为了验证接口是否能正常通信
                except Exception as e:
                    reponse_data = 'ssh接口有问题，请联系管理员处理'
                    print(reponse_data + str(e))
                    logger.error(reponse_data + str(e))
                    return JsonResponse({'result': reponse_data, 'status': False})
                else:
                    if 'Permission denied, please try again' in json.dumps(rpost.json()):
                        response_data = {'result': '用户名或密码错误', 'status': False}
                        print('minion部署失败了用户名或密码错误',rpost.json())
                        return JsonResponse(response_data)
                    elif 'Connection refused' in json.dumps(rpost.json()):
                        response_data = {'result': '无法连接%s,请确认IP是否正确' % server_ip, 'status': False}
                        print('minion部署失败了无法连接该地址', rpost.json())
                        return JsonResponse(response_data)
                    elif '"return": true' in json.dumps(rpost.json()):
                        print('连通性以及用户名密码验证成功')
                        # 如果目标主机验证没有问题则开始执行部署工作，我有个想法是ajax写2层嵌套，就是验证做一层成功先在页面
                        # 返回一个成功的提示并且显示开始部署然后再到后台执行部署，不过没仔细想如何实现，这里就先不做两层直接后台一次处理
                        minion_data = {'client': 'ssh',
                                'tgt': server_ip,
                                'fun': 'state.sls',
                                # 注意下面pillar的写法，主要是双引号内带单引号或者单引号内带双引号，不要全用单引号或双引号不然会报错
                                'arg': ["minion", "pillar={'minion_id':'%s','master':'%s'}" % (minion_id, master)]
                                }
                        try:
                            minion_post = requests.post('%s/run' % settings.SITE_SALT_API_URL, json=minion_data)
                            minion_post.raise_for_status()
                        except Exception as e:
                            minion_response = '主机%s部署minion客户端失败请联系管理员：' % server_ip
                            print(minion_response + str(e))
                            logger.error(minion_response + str(e))
                            # return logger.info(e + ' 无法获取数据')
                            return JsonResponse({'result': minion_response, 'status': False})
                        else:
                            # 格式化输出
                            data_list = ssh_format_state(minion_post.json())
                            minion_response = {'result': data_list, 'status': True}
                            return JsonResponse(minion_response)
                    else:
                        response_data = {'result': '无法连接%s,请确认master是否可以和客户机通信' % server_ip, 'status': False}
                        logger.error('minion部署失败了请确认master是否可以和客户机通信' + str(rpost.json()))
                        return JsonResponse(response_data)
    except Exception as e:
        logger.error('minion安装部署报错：', e)


# minion管理
def minion_manage(request):
    try:
        # 这里主要是担心通过ajax提交了get请求，其实多此一举因为这个页面没有ajax的get请求哈哈
        if request.is_ajax() is not True:
            if request.method == 'GET':
                search_field = request.GET.get('search_field', '')
                search_content = request.GET.get('search_content', '')
                if search_content is '':
                    minion_data = MinionList.objects.all().order_by('create_date')
                    data_list = getPage(request, minion_data, 12)
                else:
                    if search_field == 'search_minion_id':
                        minion_data = MinionList.objects.filter(minion_id__icontains=search_content).order_by(
                            'create_date')
                        data_list = getPage(request, minion_data, 12)
                    elif search_field == 'search_minion_sys':
                        minion_data = MinionList.objects.filter(sys__icontains=search_content).order_by(
                            'create_date')
                        data_list = getPage(request, minion_data, 12)
                    elif search_field == 'search_minion_status':
                        minion_data = MinionList.objects.filter(minion_status__icontains=search_content).order_by(
                            'create_date')
                        data_list = getPage(request, minion_data, 12)
                    else:
                        minion_data = MinionList.objects.filter(ip__icontains=search_content).order_by(
                            'create_date')
                        data_list = getPage(request, minion_data, 12)
                return render(request, 'saltstack/minion_manage.html',
                              {'data_list': data_list, 'search_field': search_field, 'search_content': search_content})

    except Exception as e:
        logger.error('minion管理页面有问题', e)
        return render(request, 'saltstack/minion_manage.html')


# minion管理ajax
def minion_manage_ajax(request):
    result = {'result': None, 'status': False}
    try:
        if request.is_ajax():
            # 在ajax提交时候多一个字段作为标识，来区分多个ajax提交哈，厉害！
            if request.POST.get('minion_manage_key') == 'update_minion_description':
                minion_id = request.POST.get('minion_id')
                description = request.POST.get('description')
                if len(description) > 200:
                    result['result'] = '备注内容不得超过200字'
                else:
                    MinionList.objects.filter(minion_id=minion_id).update(
                        update_time=time.strftime('%Y年%m月%d日 %X'),
                        description=description)
                    result['result'] = '修改成功'
                    result['status'] = True
                return JsonResponse(result)
            elif request.POST.get('minion_manage_key') == 'update_minion_list':
                update_result = cron.minion_status()
                if update_result:
                    result['result'] = '更新成功'
                    result['status'] = True
                else:
                    result['result'] = '更新失败'
                return JsonResponse(result)
            elif request.POST.get('minion_manage_key') == 'update_minion_status':
                minion_list = MinionList.objects.values_list('minion_id', flat=True)
                id_list = []
                with requests.Session() as s:
                    saltapi = SaltAPI(session=s)
                    if saltapi.get_token() is False:
                        logger.error('minion管理更新状态操作获取SaltAPI调用get_token请求出错')
                        result['result'] = 'minion管理更新状态操作获取SaltAPI调用get_token请求出错'
                        return JsonResponse(result)
                    else:
                        # salt检测minion最准的方法salt-run manage.status
                        response_data = saltapi.saltrun_manage_status_api()
                        if response_data is False:
                            logger.error('minion管理更新状态，操作saltrun_manage_status_api调用API失败了')
                            result['result'] = 'minion管理更新状态，操作saltrun_manage_status_api调用API失败了'
                            return JsonResponse(result)
                        else:
                            status_up = response_data['return'][0]['up']
                            for minion_id in status_up:
                                updated_values = {'minion_id': minion_id, 'minion_status': '在线',
                                                  'update_time': time.strftime('%Y年%m月%d日 %X')}
                                MinionList.objects.update_or_create(minion_id=minion_id, defaults=updated_values)
                            status_down = response_data['return'][0]['down']
                            for minion_id in status_down:
                                updated_values = {'minion_id': minion_id, 'minion_status': '离线',
                                                  'update_time': time.strftime('%Y年%m月%d日 %X')}
                                MinionList.objects.update_or_create(minion_id=minion_id, defaults=updated_values)
                            id_list.extend(status_up)
                            id_list.extend(status_down)
                            for minion_id in minion_list:
                                if minion_id not in id_list:
                                    MinionList.objects.filter(minion_id=minion_id).delete()
                            result['result'] = '更新成功'
                            result['status'] = True
                return JsonResponse(result)
            elif request.POST.get('minion_manage_key') == 'update_minion_id':
                minion_id = request.POST.get('minion_id')
                with requests.Session() as s:
                    saltapi = SaltAPI(session=s)
                    if saltapi.get_token() is False:
                        logger.error('minion管理更新操作获取SaltAPI调用get_token请求出错')
                        result['result'] = 'minion管理更新操作获取SaltAPI调用get_token请求出错'
                        return JsonResponse(result)
                    else:
                        response_data = saltapi.test_api(tgt=minion_id)
                        # 当调用api失败的时候比如salt-api服务stop了会返回false
                        if response_data is False:
                            logger.error('minion管理更新test.ping失败可能代入的参数有问题，SaltAPI调用test_api请求出错')
                            result['result'] = 'minion管理更新test.ping失败可能代入的参数有问题，SaltAPI调用test_api请求出错'
                            return JsonResponse(result)
                        # 判断返回值如果为[{}]表明没有这个minion_id
                        elif response_data['return'] != [{}]:
                            # 正常结果类似这样：{'return': [{'192.168.68.51': False, '192.168.68.1': True, '192.168.68.50-master': True}]}
                            if response_data['return'][0][minion_id]:
                                try:
                                    grains_data = saltapi.grains_itmes_api(tgt=minion_id)
                                    # 这里获取了所有minion的grains内容，如果以后表字段有增加就从这里取方便
                                    value = grains_data['return'][0][minion_id]
                                    try:
                                        value['ipv4'].remove('127.0.0.1')
                                    except Exception as e:
                                        pass
                                    try:
                                        # 下面这段代码之前都是直接用cpu_model = value['cpu_model'] 后面发现centos6和7有的有这个key有的没有导致会
                                        # 报错，所以改成用get来获取key安全哈哈
                                        ip = value.get('ipv4')
                                        os = value.get('os') + value.get('osrelease')
                                        saltversion = value.get('saltversion')
                                        sn = value.get('serialnumber')
                                        cpu_num = value.get('num_cpus')
                                        cpu_model = value.get('cpu_model')
                                        sys = value.get('kernel')
                                        kernel = value.get('kernelrelease')
                                        productname = value.get('productname')
                                        ipv4_addr = value.get('ip4_interfaces')
                                        mac_addr = value.get('hwaddr_interfaces')
                                        localhost = value.get('localhost')
                                        mem_total = value.get('mem_total')
                                    except Exception as e:
                                        # 有出现过某个minion的依赖文件被删除了但是minion进程还在，导致grains.items没有结果返回
                                        # 这样就会出现vlaue不是一个字典而是是一个str正常value内容是{'ipv4':'xxxxx'}异常时候会是'grains.items is false'
                                        # 具体是什么str没记住哈哈，不过由于不少字典而又用了get来获取字典值所以会触发try的错误，也就有了下面的操作
                                        MinionList.objects.filter(minion_id=minion_id).update(minion_status='异常',
                                                                                        update_time=time.strftime('%Y年%m月%d日 %X'))
                                    else:
                                        MinionList.objects.filter(minion_id=minion_id).update(minion_status='在线', ip=ip,
                                                          sn=sn, cpu_num=cpu_num, cpu_model=cpu_model, sys=sys,
                                                          kernel=kernel, product_name=productname, ipv4_address=ipv4_addr,
                                                          mac_address=mac_addr, localhost=localhost, mem_total=mem_total,
                                                          minion_version=saltversion, system_issue=os,
                                                          update_time=time.strftime('%Y年%m月%d日 %X'))
                                except Exception as e:
                                    logger.error('minion更新数据出错1，请检查'+ str(e))
                                    result['result'] = 'minion更新数据出错1，请检查'+ str(e)
                                    return JsonResponse(result)
                            else:
                                try:
                                    # minion离线
                                    MinionList.objects.filter(minion_id=minion_id).update(minion_status='离线',
                                                                                            update_time=time.strftime('%Y年%m月%d日 %X'))
                                except Exception as e:
                                    logger.error('minion更新数据出错2，请检查' + str(e))
                                    result['result'] = 'minion更新数据出错2，请检查' + str(e)
                                    return JsonResponse(result)
                        else:
                            logger.error('minion更新test.ping检测失败，请确认minion是否存在。。')
                            result['result'] = 'minion更新test.ping检测失败，请确认minion是否存在。。'
                            return JsonResponse(result)
                result['result'] = '更新成功'
                result['status'] = True
                return JsonResponse(result)
            else:
                result['result'] = 'minion管理页ajax提交了错误的tag'
                return JsonResponse(result)
    except Exception as e:
        logger.error('minion管理ajax提交处理有问题', e)
        result['result'] = 'minion管理ajax提交处理有问题'
        return JsonResponse(result)


# salt命令集
def salt_cmd_manage(request):
    try:
        if request.is_ajax() is not True:
            if request.method == 'GET':
                search_field = request.GET.get('search_field', '')
                search_content = request.GET.get('search_content', '')
                if search_content is '':
                    data = SaltCmdInfo.objects.all().order_by('salt_cmd_type','salt_cmd')
                    data_list = getPage(request, data, 12)
                else:
                    if search_field == 'any':
                        data = SaltCmdInfo.objects.filter(salt_cmd__icontains=search_content).order_by('salt_cmd_type',
                                                                                                       'salt_cmd')
                        data_list = getPage(request, data, 12)
                    elif search_field in ['module', 'state', 'runner']:
                        data = SaltCmdInfo.objects.filter(salt_cmd_type__icontains=search_field,
                                                          salt_cmd__icontains=search_content).order_by('salt_cmd_type',
                                                                                                       'salt_cmd')
                        data_list = getPage(request, data, 12)
                    else:
                        return render(request, 'saltstack/salt_cmd_manage.html')
                return render(request, 'saltstack/salt_cmd_manage.html',
                              {'data_list': data_list, 'search_field': search_field, 'search_content': search_content})
    except Exception as e:
        logger.error('salt命令集页面有问题', e)
        return render(request, 'saltstack/salt_cmd_manage.html')


# salt命令集ajax操作
def salt_cmd_manage_ajax(request):
    result = {'result': None, 'status': False}
    try:
        if request.is_ajax():
            # 在ajax提交时候多一个字段作为标识，来区分多个ajax提交哈，厉害！
            if request.GET.get('salt_cmd_tag_key') == 'modal_search_minion_id':
                minion_id = request.GET.get('minion_id')
                minion_id_list = MinionList.objects.filter(minion_id__icontains=minion_id).order_by(
                    'create_date').values_list('minion_id', flat=True)
                result['result'] = list(minion_id_list)
                result['status'] = True
                return JsonResponse(result)
            elif request.POST.get('salt_cmd_tag_key') == 'collection_info':
                minion_id = request.POST.get('minion_id')
                collection_style = request.POST.get('collection_style')
                try:
                    with requests.Session() as s:
                        saltapi = SaltAPI(session=s)
                        if saltapi.get_token() is False:
                            error_data = 'salt命令集采集信息获取SaltAPI调用get_token请求出错'
                            result['result'] = error_data
                            return JsonResponse(result)
                        else:
                            if collection_style == 'state':
                                response_data = saltapi.sys_state_doc_api(tgt=minion_id, tgt_type='list')
                            elif collection_style == 'runner':
                                response_data = saltapi.sys_runner_doc_api(tgt=minion_id, tgt_type='list')
                            else:
                                response_data = saltapi.sys_doc_api(tgt=minion_id, tgt_type='list')
                            # 当调用api失败的时候会返回false
                            if response_data is False:
                                error_data = 'salt命令集采集信息失败，SaltAPI调用采集api请求出错'
                                result['result'] = error_data
                                return JsonResponse(result)
                            else:
                                response_data = response_data['return'][0]
                                try:
                                    # 用来存放掉线或者访问不到的minion_id信息
                                    info = ''
                                    # state的使用帮助特殊，比如cmd.run会有一个头cmd的说明，所以要对cmd这样做一个处理把他加入到cmd.run的使用帮助中
                                    if collection_style == 'state':
                                        a = {}
                                        b = {}
                                        for min_id, cmd_dict in response_data.items():
                                            if isinstance(cmd_dict, dict):
                                                for salt_cmd, salt_cmd_doc in cmd_dict.items():
                                                    if len(salt_cmd.split('.')) == 1:
                                                        a[salt_cmd] = salt_cmd_doc
                                                    else:
                                                        b[salt_cmd] = salt_cmd_doc
                                                for salt_cmd in b.keys():
                                                    try:
                                                        b[salt_cmd] = salt_cmd.split('.')[0] + ':\n' + str(
                                                            a[salt_cmd.split('.')[0]]).replace('\n',
                                                                                           '\n    ') + '\n\n' + salt_cmd + ':\n' + str(
                                                            b[salt_cmd])
                                                    except Exception as e:
                                                        logger.error('state采集后台错误：' + str(e))
                                                        result['result'] = 'state采集后台错误：' + str(e)
                                                        return JsonResponse(result)
                                                    updated_values = {'salt_cmd': salt_cmd, 'salt_cmd_type': collection_style,
                                                                      'salt_cmd_module': salt_cmd.split('.')[0],
                                                                      'salt_cmd_source': 'minion', 'salt_cmd_doc': b[salt_cmd],
                                                                      'update_time': time.strftime('%Y年%m月%d日 %X')}
                                                    SaltCmdInfo.objects.update_or_create(salt_cmd=salt_cmd, salt_cmd_type=collection_style, defaults=updated_values)
                                            elif isinstance(cmd_dict, bool):
                                                info += ' 不过minion_id:' + min_id + '掉线了没有从它采集到数据'
                                        result['result'] = '采集完成' + info
                                        result['status'] = True
                                        return JsonResponse(result)
                                    else:
                                        for min_id, cmd_dict in response_data.items():
                                            if isinstance(cmd_dict, dict):
                                                for salt_cmd, salt_cmd_doc in cmd_dict.items():
                                                    salt_cmd_doc = str(salt_cmd) + ':\n' + str(salt_cmd_doc)
                                                    updated_values = {'salt_cmd': salt_cmd, 'salt_cmd_type': collection_style,
                                                                      'salt_cmd_module': salt_cmd.split('.')[0],
                                                                      'salt_cmd_source': 'minion', 'salt_cmd_doc': salt_cmd_doc,
                                                                      'update_time': time.strftime('%Y年%m月%d日 %X')}
                                                    SaltCmdInfo.objects.update_or_create(salt_cmd=salt_cmd, salt_cmd_type=collection_style, defaults=updated_values)
                                            elif isinstance(cmd_dict, bool):
                                                info += ' 不过minion_id:' + min_id + '掉线了没有从它采集到数据'
                                        result['result'] = '采集完成' + info
                                        result['status'] = True
                                        return JsonResponse(result)
                                except Exception as e:
                                    logger.error('采集后台错误：' + str(e))
                                    result['result'] = '采集后台错误：' + str(e)
                                    return JsonResponse(result)
                except Exception as e:
                    logger.error('采集信息出错：'+str(e))
                    result['result'] = '采集信息出错'
                    return JsonResponse(result)
            elif request.POST.get('salt_cmd_tag_key') == 'update_salt_cmd_description':
                salt_cmd = request.POST.get('salt_cmd')
                description = request.POST.get('description')
                try:
                    SaltCmdInfo.objects.filter(salt_cmd=salt_cmd).update(update_time=time.strftime('%Y年%m月%d日 %X'),
                                                                         description=description)
                    result['result'] = '修改成功'
                    result['status'] = True
                except Exception as e:
                    message = '修改失败', str(e)
                    logger.error(message)
                    result['result'] = message
                return JsonResponse(result)
            elif request.POST.get('salt_cmd_tag_key') == 'salt_cmd_delete':
                salt_cmd = request.POST.get('salt_cmd')
                try:
                    SaltCmdInfo.objects.filter(salt_cmd=salt_cmd).delete()
                    result['result'] = '成功'
                    result['status'] = True
                except Exception as e:
                    message = '修改失败', str(e)
                    logger.error(message)
                    result['result'] = message
                return JsonResponse(result)
    except Exception as e:
        logger.error('salt命令集ajax提交处理有问题', e)
        result['result'] = 'salt命令集ajax提交处理有问题'
        return JsonResponse(result)


# SaltKey管理
def saltkey_manage(request):
    try:
        if request.method == 'GET':
            accepted_count = SaltKeyList.objects.filter(certification_status='accepted').count()
            unaccepted_count = SaltKeyList.objects.filter(certification_status='unaccepted').count()
            denied_count = SaltKeyList.objects.filter(certification_status='denied').count()
            rejected_count = SaltKeyList.objects.filter(certification_status='rejected').count()
            if request.GET.get('status') is None:
                return HttpResponseRedirect('/saltkey_manage/?status=accepted&search=')
            if request.GET.get('status') == 'accepted':
                if request.GET.get('search').strip() is "":
                    accepted_data = SaltKeyList.objects.filter(certification_status='accepted')
                    data_list = getPage(request, accepted_data, 8)
                    return render(request, 'saltstack/saltkey_manage.html',
                                  {'data_list': data_list, 'accepted_count': accepted_count,
                                   'unaccepted_count': unaccepted_count, 'denied_count': denied_count,
                                   'rejected_count': rejected_count, 'search': ""})
                else:
                    search_data = request.GET.get('search').strip()
                    accepted_data = SaltKeyList.objects.filter(minion_id__icontains=search_data, certification_status='accepted')
                    data_list = getPage(request, accepted_data, 8)
                    return render(request, 'saltstack/saltkey_manage.html',
                                  {'data_list': data_list, 'accepted_count': accepted_count,
                                   'unaccepted_count': unaccepted_count, 'denied_count': denied_count,
                                   'rejected_count': rejected_count, 'search': search_data})
            elif request.GET.get('status') == 'unaccepted':
                if request.GET.get('search').strip() is "":
                    unaccepted_data = SaltKeyList.objects.filter(certification_status='unaccepted')
                    data_list = getPage(request, unaccepted_data, 8)
                    return render(request, 'saltstack/saltkey_manage_unaccepted.html',
                                  {'data_list': data_list, 'accepted_count': accepted_count,
                                   'unaccepted_count': unaccepted_count, 'denied_count': denied_count,
                                   'rejected_count': rejected_count, 'search': ""})
                else:
                    search_data = request.GET.get('search').strip()
                    unaccepted_data = SaltKeyList.objects.filter(minion_id__icontains=search_data, certification_status='unaccepted')
                    data_list = getPage(request, unaccepted_data, 8)
                    return render(request, 'saltstack/saltkey_manage_unaccepted.html',
                                  {'data_list': data_list, 'accepted_count': accepted_count,
                                   'unaccepted_count': unaccepted_count, 'denied_count': denied_count,
                                   'rejected_count': rejected_count, 'search': search_data})
            elif request.GET.get('status') == 'denied':
                if request.GET.get('search').strip() is "":
                    denied_data = SaltKeyList.objects.filter(certification_status='denied')
                    data_list = getPage(request, denied_data, 8)
                    return render(request, 'saltstack/saltkey_manage_denied.html',
                                  {'data_list': data_list, 'accepted_count': accepted_count,
                                   'unaccepted_count': unaccepted_count, 'denied_count': denied_count,
                                   'rejected_count': rejected_count, 'search': ""})
                else:
                    search_data = request.GET.get('search').strip()
                    denied_data = SaltKeyList.objects.filter(minion_id__icontains=search_data, certification_status='denied')
                    data_list = getPage(request, denied_data, 8)
                    return render(request, 'saltstack/saltkey_manage_denied.html',
                                  {'data_list': data_list, 'accepted_count': accepted_count,
                                   'unaccepted_count': unaccepted_count, 'denied_count': denied_count,
                                   'rejected_count': rejected_count, 'search': search_data})
            elif request.GET.get('status') == 'rejected':
                if request.GET.get('search').strip() is "":
                    rejected_data = SaltKeyList.objects.filter(certification_status='rejected')
                    data_list = getPage(request, rejected_data, 8)
                    return render(request, 'saltstack/saltkey_manage_rejected.html',
                                  {'data_list': data_list, 'accepted_count': accepted_count,
                                   'unaccepted_count': unaccepted_count, 'denied_count': denied_count,
                                   'rejected_count': rejected_count, 'search': ""})
                else:
                    search_data = request.GET.get('search').strip()
                    rejected_data = SaltKeyList.objects.filter(minion_id__icontains=search_data, certification_status='rejected')
                    data_list = getPage(request, rejected_data, 8)
                    return render(request, 'saltstack/saltkey_manage_rejected.html',
                                  {'data_list': data_list, 'accepted_count': accepted_count,
                                   'unaccepted_count': unaccepted_count, 'denied_count': denied_count,
                                   'rejected_count': rejected_count, 'search': search_data})

    except Exception as e:
        logger.error('SaltKey管理页面有问题', e)
        return render(request, 'saltstack/saltkey_manage.html')


# SaltKey全局操作
def salt_key_global(request):
    try:
        if request.is_ajax():
            if 'global_flush_salt_key' in request.POST:
                if cron.saltkey_list():
                    return JsonResponse({'result': '操作成功', 'status': True})
                else:
                    return JsonResponse({'result': '操作失败', 'status': False})
    except Exception as e:
        logger.error('全局操作出错了' + str(e))
        response_data = {'result': '操作失败', 'status': False}
        return JsonResponse(response_data)


# salt的test.ping方法
def salt_test_ping(request):
    try:
        if request.is_ajax():
            minion_id = request.POST.get('minion_id')
            with requests.Session() as s:
                saltapi = SaltAPI(session=s)
                if saltapi.get_token() is False:
                    logger.error('test.ping操作获取SaltAPI调用get_token请求出错')
                    response_data = {'result': '检测失败', 'status': False}
                    return JsonResponse(response_data)
                else:
                    response_data = saltapi.test_api(tgt=minion_id)
                    # 当调用api失败的时候比如salt-api服务stop了会返回false
                    if response_data is False:
                        logger.error('test.ping失败可能代入的参数有问题，SaltAPI调用test_api请求出错')
                        response_data = {'result': '检测失败', 'status': False}
                        return JsonResponse(response_data)
                    # 判断返回值如果为[{}]表明没有这个minion_id
                    elif response_data['return'] != [{}]:
                        # 正常结果类似这样：{'return': [{'192.168.68.51': False, '192.168.68.1': True, '192.168.68.50-master': True}]}
                        data_source = response_data['return'][0]
                        response_data = {'result': data_source, 'status': True}
                        return JsonResponse(response_data)
                    else:
                        logger.error('test.ping检测失败，请确认minion是否存在。。')
                        response_data = {'result': '检测失败', 'status': False}
                        return JsonResponse(response_data)
    except Exception as e:
        logger.error('test.ping检测出错了' + str(e))
        response_data = {'result': '检测失败', 'status': False}
        return JsonResponse(response_data)


# salt的删除key方法
def salt_key_delete(request):
    try:
        if request.is_ajax():
            minion_id = request.POST.getlist('minion_id')
            with requests.Session() as s:
                saltapi = SaltAPI(session=s)
                if saltapi.get_token() is False:
                    logger.error('删除key操作获取SaltAPI调用get_token请求出错')
                    response_data = {'result': '删除失败', 'status': False}
                    return JsonResponse(response_data)
                else:
                    response_data = saltapi.saltkey_delete_api(match=minion_id)
                    # 当调用api失败的时候会返回false
                    if response_data is False:
                        logger.error('删除key失败可能代入的参数有问题，SaltAPI调用saltkey_delete_api请求出错')
                        response_data = {'result': '删除失败', 'status': False}
                        return JsonResponse(response_data)
                    # 返回值不会有为[{}]的情况所以没出现api失败就表示成功，这是这个delete的api接口的坑奶奶的
                    else:
                        if cron.saltkey_list():
                            response_data = {'result': '删除成功', 'status': True}
                            return JsonResponse(response_data)
                        else:
                            logger.error('删除key在执行刷新saltkey操作即cron.py里的方法时候出错了')
                            response_data = {'result': '删除失败', 'status': False}
                            return JsonResponse(response_data)
    except Exception as e:
        logger.error('删除key出错了' + str(e))
        response_data = {'result': '删除失败', 'status': False}
        return JsonResponse(response_data)


# salt的删除denied下的key方法
def salt_key_denied_delete(request):
    try:
        if request.is_ajax():
            # 默认获取列表主要是为了后面做批量删除可以复用这个方法
            minion_id = request.POST.getlist('minion_id')
            # 因为在linux中批量删除文件要用{1.txt,2.txt,a.txt}或者1.txt 2.txt a.txt空格隔开即可所以要格式化下把上面列表转成这样子
            # 本来我是要用{1.txt,2.txt,a.txt}但是在遇到单个文件的时候{1.txt}不行{1.txt,}可以但是删除的含义不同了会导致master挂掉草
            # 所以最终使用进入到minions_denied文件夹然后1.txt 2.txt a.txt空格隔开每个文件删除的方式删除
            minion_id = ' '.join(minion_id)
            with requests.Session() as s:
                saltapi = SaltAPI(session=s)
                if saltapi.get_token() is False:
                    logger.error('删除key操作获取SaltAPI调用get_token请求出错')
                    response_data = {'result': '删除失败', 'status': False}
                    return JsonResponse(response_data)
                else:
                    response_data = saltapi.cmd_run_api(tgt=settings.SITE_SALT_MASTER, arg='cd /etc/salt/pki/master/minions_denied/ && rm -rf %s' % minion_id)
                    # 当调用api失败的时候会返回false
                    if response_data is False:
                        logger.error('删除denied的key失败可能代入的参数有问题，SaltAPI调用cmd.run请求出错')
                        response_data = {'result': '删除失败', 'status': False}
                        return JsonResponse(response_data)
                    # 命令rm删除返回值为空，所以return值是[{}]这个值不是空哟所以没出现api失败就表示成功
                    else:
                        if cron.saltkey_list():
                            response_data = {'result': '删除成功', 'status': True}
                            return JsonResponse(response_data)
                        else:
                            logger.error('删除denied的key在执行刷新saltkey操作即cron.py里的方法时候出错了')
                            response_data = {'result': '删除失败', 'status': False}
                            return JsonResponse(response_data)
    except Exception as e:
        logger.error('删除denied的key出错了' + str(e))
        response_data = {'result': '删除失败', 'status': False}
        return JsonResponse(response_data)


# 接受salt-key方法saltkey_accept_api
def salt_key_accept(request):
    try:
        if request.is_ajax():
            minion_id = request.POST.getlist('minion_id')
            with requests.Session() as s:
                saltapi = SaltAPI(session=s)
                if saltapi.get_token() is False:
                    logger.error('接受key操作获取SaltAPI调用get_token请求出错')
                    response_data = {'result': '删除失败', 'status': False}
                    return JsonResponse(response_data)
                else:
                    response_data = saltapi.saltkey_accept_api(match=minion_id)
                    # 当调用api失败的时候会返回false
                    if response_data is False:
                        logger.error('接受key失败可能代入的参数有问题，SaltAPI调用saltkey_accept_api请求出错')
                        response_data = {'result': '接受失败', 'status': False}
                        return JsonResponse(response_data)
                    # 返回值不会有为[{}]的情况所以没出现api失败就表示成功，这是这个delete的api接口的坑奶奶的
                    else:
                        if cron.saltkey_list():
                            response_data = {'result': '接受成功', 'status': True}
                            return JsonResponse(response_data)
                        else:
                            logger.error('接受key在执行刷新saltkey操作即cron.py里的方法时候出错了')
                            response_data = {'result': '接受失败', 'status': False}
                            return JsonResponse(response_data)
    except Exception as e:
        logger.error('接受key出错了' + str(e))
        response_data = {'result': '接受失败', 'status': False}
        return JsonResponse(response_data)


# 拒绝salt-key方法saltkey_accept_api
def salt_key_reject(request):
    try:
        if request.is_ajax():
            minion_id = request.POST.getlist('minion_id')
            with requests.Session() as s:
                saltapi = SaltAPI(session=s)
                if saltapi.get_token() is False:
                    logger.error('拒绝key操作获取SaltAPI调用get_token请求出错')
                    response_data = {'result': '拒绝失败', 'status': False}
                    return JsonResponse(response_data)
                else:
                    response_data = saltapi.saltkey_reject_api(match=minion_id)
                    # 当调用api失败的时候会返回false
                    if response_data is False:
                        logger.error('拒绝key失败可能代入的参数有问题，SaltAPI调用saltkey_reject_api请求出错')
                        response_data = {'result': '拒绝失败', 'status': False}
                        return JsonResponse(response_data)
                    # 返回值不会有为[{}]的情况所以没出现api失败就表示成功，这是这个delete的api接口的坑奶奶的
                    else:
                        if cron.saltkey_list():
                            response_data = {'result': '拒绝成功', 'status': True}
                            return JsonResponse(response_data)
                        else:
                            logger.error('拒绝key在执行刷新saltkey操作即cron.py里的方法时候出错了')
                            response_data = {'result': '拒绝失败', 'status': False}
                            return JsonResponse(response_data)
    except Exception as e:
        logger.error('拒绝key出错了' + str(e))
        response_data = {'result': '拒绝失败', 'status': False}
        return JsonResponse(response_data)


# salt_exe执行salt命令页
def salt_exe(request):
    try:
        if request.method == 'GET' and not request.is_ajax():
            data_list = SaltCmdInfo.objects.filter(salt_cmd_type='module').values('salt_cmd_module').distinct().order_by('salt_cmd_module')
            return render(request, 'saltstack/salt_exe.html', {'data_list': data_list})
    except Exception as e:
        logger.error('salt命令执行页面有问题：', e)
        return render(request, 'saltstack/salt_exe.html')


# salt_exe_ajax执行salt命令ajax操作
def salt_exe_ajax(request):
    result = {'result': None, 'status': False}
    app_log = []
    try:
        if request.is_ajax():
            # 在ajax提交时候多一个字段作为标识，来区分多个ajax提交哈，厉害！
            if request.GET.get('salt_exe_tag_key') == 'modal_search_minion_id':
                minion_id = request.GET.get('minion_id')
                minion_id_list = MinionList.objects.filter(minion_id__icontains=minion_id).order_by(
                    'create_date').values_list('minion_id', flat=True)
                result['result'] = list(minion_id_list)
                result['status'] = True
                return JsonResponse(result)
            elif request.GET.get('salt_exe_tag_key') == 'search_salt_module':
                salt_cmd_type = request.GET.get('salt_cmd_type')
                salt_cmd_list = SaltCmdInfo.objects.filter(salt_cmd_type=salt_cmd_type).values_list(
                    'salt_cmd_module', flat=True).distinct().order_by('salt_cmd_module')
                result['result'] = list(salt_cmd_list)
                result['status'] = True
                return JsonResponse(result)
            elif request.GET.get('salt_exe_tag_key') == 'search_salt_cmd':
                salt_cmd_type = request.GET.get('salt_cmd_type')
                salt_cmd_module = request.GET.get('salt_cmd_module')
                salt_cmd_list = SaltCmdInfo.objects.filter(salt_cmd_type=salt_cmd_type,
                                                           salt_cmd_module=salt_cmd_module).values_list('salt_cmd',
                                                                                                        flat=True)
                result['result'] = list(salt_cmd_list)
                result['status'] = True
                return JsonResponse(result)
            elif request.GET.get('salt_exe_tag_key') == 'search_salt_cmd_doc':
                salt_cmd = request.GET.get('salt_cmd')
                salt_cmd_type = request.GET.get('salt_cmd_type')
                salt_cmd_data = SaltCmdInfo.objects.filter(salt_cmd=salt_cmd, salt_cmd_type=salt_cmd_type).first()
                result['result'] = salt_cmd_data.salt_cmd_doc if salt_cmd_data else '查询结果为空，请确认模块和命令是否填写正确'
                result['status'] = True
                return JsonResponse(result)
            elif request.POST.get('salt_exe_tag_key') == 'salt_exe':
                client = request.POST.get('client')
                tgt = request.POST.get('tgt')
                tgt_type = request.POST.get('tgt_type')
                fun = request.POST.get('fun')
                arg = request.POST.getlist('arg')
                # 这是判断arg是否传输值过来，如果没有前端会传个['']过来，这是由于我前端设置了的
                if arg == ['']:
                    arg = None
                if tgt_type == 'list':
                    tgt = [tgt]
                if client != 'runner':
                    data = {'client': client, 'tgt': tgt, 'tgt_type': tgt_type, 'fun': fun, 'arg': arg}
                else:
                    data = {'client': client, 'fun': fun, 'arg': arg}
                with requests.Session() as s:
                    saltapi = SaltAPI(session=s)
                    if saltapi.get_token() is False:
                        app_log.append('\nsalt命令执行后台出错_error(0)，请联系管理员')
                        result['result'] = app_log
                        return JsonResponse(result)
                    else:
                        response_data = saltapi.public(data=data)
                        # 当调用api失败的时候会返回false
                        if response_data is False:
                            app_log.append('\nsalt命令执行后台出错_error(1)，请联系管理员')
                            result['result'] = app_log
                            return JsonResponse(result)
                        else:
                            try:
                                response_data = response_data['return'][0]
                                result['status'] = True
                                result['result'] = response_data
                                return JsonResponse(result)
                            except Exception as e:
                                app_log.append('\n' + 'salt命令执行失败_error(2):' + str(response_data))
                                result['result'] = app_log
                                return JsonResponse(result)
            elif request.GET.get('salt_exe_tag_key') == 'search_jid_status':
                jid = request.GET.get('jid')
                with requests.Session() as s:
                    saltapi = SaltAPI(session=s)
                    if saltapi.get_token() is False:
                        app_log.append('\nsalt命令执行查询jid后台出错_error(0)，请联系管理员')
                        result['result'] = app_log
                        return JsonResponse(result)
                    else:
                        response_data = saltapi.job_exit_success_api(jid=jid)
                        # 当调用api失败的时候会返回false
                        if response_data is False:
                            app_log.append('\nsalt命令执行查询jid后台出错_error(1)，请联系管理员')
                            result['result'] = app_log
                            return JsonResponse(result)
                        else:
                            try:
                                response_data = response_data['return'][0]
                                result['status'] = True
                                result['result'] = response_data
                                return JsonResponse(result)
                            except Exception as e:
                                app_log.append('\n' + 'salt命令执行执行查询jid失败_error(2):' + str(response_data))
                                result['result'] = app_log
                                return JsonResponse(result)
            elif request.GET.get('salt_exe_tag_key') == 'search_jid_result':
                jid = request.GET.get('jid')
                with requests.Session() as s:
                    saltapi = SaltAPI(session=s)
                    if saltapi.get_token() is False:
                        app_log.append('\nsalt命令执行查询job结果后台出错_error(0)，请联系管理员')
                        result['result'] = app_log
                        return JsonResponse(result)
                    else:
                        response_data = saltapi.jid_api(jid=jid)
                        # 当调用api失败的时候会返回false
                        if response_data is False:
                            app_log.append('\nsalt命令执行查询job结果后台出错_error(1)，请联系管理员')
                            result['result'] = app_log
                            return JsonResponse(result)
                        else:
                            try:
                                response_data = response_data['return'][0]
                                result['status'] = True
                                result['result'] = response_data
                                return JsonResponse(result)
                            except Exception as e:
                                app_log.append('\n' + 'salt命令执行执行查询job结果失败_error(2):' + str(response_data))
                                result['result'] = app_log
                                return JsonResponse(result)
    except Exception as e:
        logger.error('salt命令执行ajax提交处理有问题', e)
        result['result'] = 'salt命令执行ajax提交处理有问题'
        return JsonResponse(result)


# salt_tool执行salt各种封装好的命令
def salt_tool(request):
    try:
        if request.method == 'GET' and not request.is_ajax():
            return render(request, 'saltstack/salt_tool.html')
    except Exception as e:
        logger.error('salt命令集页面有问题', e)
        return render(request, 'saltstack/salt_tool.html')


# salt_tool执行salt各种封装好的命令ajax操作
def salt_tool_ajax(request):
    result = {'result': None, 'status': False}
    app_log = []
    try:
        if request.is_ajax():
            # 在ajax提交时候多一个字段作为标识，来区分多个ajax提交哈，厉害！
            if request.GET.get('salt_tool_tag_key') == 'modal_search_minion_id':
                minion_id = request.GET.get('minion_id')
                minion_id_list = MinionList.objects.filter(minion_id__icontains=minion_id).order_by(
                    'create_date').values_list('minion_id', flat=True)
                result['result'] = list(minion_id_list)
                result['status'] = True
                return JsonResponse(result)
            elif request.POST.get('salt_tool_tag_key') == 'create_task':
                tgt = request.POST.get('tgt')
                tgt_type = request.POST.get('tgt_type')
                task_name = request.POST.get('task_name')
                username = request.POST.get('username')
                cmd = request.POST.get('cmd')
                force = request.POST.get('force')
                start_in = request.POST.get('start_in')
                task_arg = request.POST.get('task_arg')
                arg = []
                arg.extend([task_name, 'action_type=Execute', 'user_name=%s' % username, 'cmd=%s' % cmd, 'force=%s' % force, 'execution_time_limit=False', 'trigger_type=OnBoot'])
                # 这是判断arg是否传输值过来，如果没有前端会传个['']过来，这是由于我前端设置了的
                if start_in != '':
                    arg.append('start_in=%s' % start_in)
                if task_arg != '':
                    arg.append('arguments=%s' % task_arg)
                with requests.Session() as s:
                    saltapi = SaltAPI(session=s)
                    if saltapi.get_token() is False:
                        app_log.append('\nwindows创建计划任务后台出错_error(0)，请联系管理员')
                        result['result'] = app_log
                        return JsonResponse(result)
                    else:
                        response_data = saltapi.task_create_api(tgt=tgt, tgt_type=tgt_type, arg=arg)
                        # 当调用api失败的时候会返回false
                        if response_data is False:
                            app_log.append('\nwindows创建计划任务后台出错_error(1)，请联系管理员')
                            result['result'] = app_log
                            return JsonResponse(result)
                        else:
                            try:
                                response_data = response_data['return'][0]
                                result['status'] = True
                                result['result'] = response_data
                                return JsonResponse(result)
                            except Exception as e:
                                app_log.append('\n' + 'windows创建计划任务失败_error(2):' + str(response_data))
                                result['result'] = app_log
                                return JsonResponse(result)
            elif request.GET.get('salt_tool_tag_key') == 'get_supervisor_content':
                program = request.GET.get('program')
                command = request.GET.get('command')
                directory = request.GET.get('directory')
                env = request.GET.get('env')
                logfile = request.GET.get('logfile')
                errorlogfile = request.GET.get('errorlogfile')
                arg = []
                arg.extend(['[program:%s]' % program, 'command=%s' % command, 'stdout_logfile_maxbytes=10MB',
                            'stderr_logfile_maxbytes=10MB', 'stdout_logfile_backups=5', 'stderr_logfile_backups=5',
                            'startsecs=5', 'stopsignal=QUIT', 'stopasgroup=true', 'killasgroup=true'])
                # 这是判断arg是否传输值过来，如果没有前端会传个['']过来，这是由于我前端设置了的
                if logfile != '':
                    arg.append('stdout_logfile=%s' % logfile)
                else:
                    logfile = 'stdout_logfile=/var/log/supervisor/%s.log' % program
                    arg.append(logfile)
                if errorlogfile != '':
                    arg.append('stderr_logfile=%s' % errorlogfile)
                else:
                    errorlogfile = 'stderr_logfile=/var/log/supervisor/%s.log' % program
                    arg.append(errorlogfile)
                if env != '':
                    arg.append('environment=%s' % env)
                if directory != '':
                    arg.append('directory=%s' % directory)
                result['status'] = True
                result['result'] = arg
                return JsonResponse(result)
            elif request.POST.get('salt_tool_tag_key') == 'create_supervisor':
                tgt = request.POST.get('tgt')
                tgt_type = request.POST.get('tgt_type')
                program = request.POST.get('program')
                command = request.POST.get('command')
                directory = request.POST.get('directory')
                env = request.POST.get('env')
                logfile = request.POST.get('logfile')
                errorlogfile = request.POST.get('errorlogfile')
                force = request.POST.get('force')
                # path文件存放的目录必须是supervisord.conf的include定义好的，所以无法自定义，只能内置
                path = '/etc/supervisord.d/'
                # file_path是文件路径加文件名后缀是.ini，这个也是在supervisord.conf的include定义好的格式
                file_path = path + program + '.ini'
                arg = []
                arg.extend(['[program:%s]' % program, 'command=%s' % command,'stdout_logfile_maxbytes=10MB',
                            'stderr_logfile_maxbytes=10MB', 'stdout_logfile_backups=5', 'stderr_logfile_backups=5',
                            'startsecs=5', 'stopsignal=QUIT', 'stopasgroup=true', 'killasgroup=true'])
                # 这是判断arg是否传输值过来，如果没有前端会传个['']过来，这是由于我前端设置了的
                if logfile != '':
                    logfile_path = logfile
                    arg.append('stdout_logfile=%s' % logfile_path)
                else:
                    logfile_path = '/var/log/supervisor/%s.log' % program
                    arg.append('stdout_logfile=%s' % logfile_path)
                if errorlogfile != '':
                    errorlogfile_path = errorlogfile
                    arg.append('stderr_logfile=%s' % errorlogfile_path)
                else:
                    errorlogfile_path = '/var/log/supervisor/%s.log' % program
                    arg.append('stderr_logfile=%s' % errorlogfile_path)
                if env != '':
                    arg.append('environment=%s' % env)
                if directory != '':
                    arg.append('directory=%s' % directory)
                with requests.Session() as s:
                    saltapi = SaltAPI(session=s)
                    if saltapi.get_token() is False:
                        app_log.append('\n创建supervisor进程后台出错_error(0)，请联系管理员')
                        result['result'] = app_log
                        return JsonResponse(result)
                    else:
                        response_data = saltapi.file_exists_api(tgt=tgt, tgt_type=tgt_type, arg=file_path)
                        # 当调用api失败的时候会返回false
                        if response_data is False:
                            app_log.append('\n创建supervisor进程后台出错_error(1)，请联系管理员')
                            result['result'] = app_log
                            return JsonResponse(result)
                        else:
                            try:
                                response_data = response_data['return'][0]
                                success_tgt = []
                                for k, v in response_data.items():
                                    # 判断如果执行的minion中是否已经存在了该文件夹，如果存在并且强制没有选中True就不继续执行这个minion的下一步操作
                                    if v is True and force == 'false':
                                        app_log.append({k: 'minion_id:%s已存在同名文件，如需覆盖请选择强制' % k})
                                    else:
                                        success_tgt.append(k)
                                if success_tgt:
                                    success_tgt = ','.join(success_tgt)
                                    response_data = saltapi.file_write_api(tgt=success_tgt, tgt_type='list', arg=[file_path, 'args=%s' % arg])
                                    if response_data is False:
                                        app_log.append('\n创建supervisor进程后台出错_error(2)，请联系管理员')
                                        result['result'] = app_log
                                        return JsonResponse(result)
                                    else:
                                        response_data = response_data['return']
                                        app_log.extend(response_data)
                                    # 日志文件目录创建
                                    response_data = saltapi.file_makedirs_api(tgt=success_tgt, tgt_type='list',
                                                                              arg=logfile_path)
                                    if response_data is False:
                                        app_log.append('\n创建supervisor进程日志创建出错_error(3)，请联系管理员')
                                        result['result'] = app_log
                                        return JsonResponse(result)
                                    response_data = saltapi.file_makedirs_api(tgt=success_tgt, tgt_type='list',
                                                                              arg=errorlogfile_path)
                                    if response_data is False:
                                        app_log.append('\n创建supervisor进程日志创建出错_error(4)，请联系管理员')
                                        result['result'] = app_log
                                        return JsonResponse(result)
                                    # 重载supervisord配置
                                    response_data = saltapi.supervisord_update_api(tgt=success_tgt, tgt_type='list')
                                    if response_data is False:
                                        app_log.append('\n创建supervisor进程重载配置出错_error(5)，请联系管理员')
                                        result['result'] = app_log
                                        return JsonResponse(result)
                                result['status'] = True
                                result['result'] = app_log
                                return JsonResponse(result)
                            except Exception as e:
                                app_log.append('\n' + '创建supervisor进程失败_error(3):' + str(response_data))
                                result['result'] = app_log
                                return JsonResponse(result)
            else:
                result['result'] = 'salt工具页ajax提交了错误的tag'
                return JsonResponse(result)
    except Exception as e:
        logger.error('salt命令执行ajax提交处理有问题', e)
        result['result'] = 'salt命令执行ajax提交处理有问题'
        return JsonResponse(result)


# salt_file_manage文件管理
def salt_file_manage(request):
    try:
        if request.method == 'GET' and not request.is_ajax():
            return render(request, 'saltstack/salt_file_manage.html')
    except Exception as e:
        logger.error('salt文件管理页面有问题', e)
        return render(request, 'saltstack/salt_file_manage.html')


# salt_file_manage执行文件管理命令ajax操作
def salt_file_manage_ajax(request):
    result = {'result': None, 'status': False}
    app_log = []
    try:
        if request.is_ajax():
            # 在ajax提交时候多一个字段作为标识，来区分多个ajax提交哈，厉害！
            if request.GET.get('salt_tool_tag_key') == 'modal_search_minion_id':
                minion_id = request.GET.get('minion_id')
                minion_id_list = MinionList.objects.filter(minion_id__icontains=minion_id).order_by(
                    'create_date').values_list('minion_id', flat=True)
                result['result'] = list(minion_id_list)
                result['status'] = True
                return JsonResponse(result)
            elif request.POST.get('salt_tool_tag_key') == 'create_task':
                tgt = request.POST.get('tgt')
                tgt_type = request.POST.get('tgt_type')
                task_name = request.POST.get('task_name')
                username = request.POST.get('username')
                cmd = request.POST.get('cmd')
                force = request.POST.get('force')
                start_in = request.POST.get('start_in')
                task_arg = request.POST.get('task_arg')
                arg = []
                arg.extend([task_name, 'action_type=Execute', 'user_name=%s' % username, 'cmd=%s' % cmd, 'force=%s' % force, 'execution_time_limit=False', 'trigger_type=OnBoot'])
                # 这是判断arg是否传输值过来，如果没有前端会传个['']过来，这是由于我前端设置了的
                if start_in != '':
                    arg.append('start_in=%s' % start_in)
                if task_arg != '':
                    arg.append('arguments=%s' % task_arg)
                with requests.Session() as s:
                    saltapi = SaltAPI(session=s)
                    if saltapi.get_token() is False:
                        app_log.append('\nwindows创建计划任务后台出错_error(0)，请联系管理员')
                        result['result'] = app_log
                        return JsonResponse(result)
                    else:
                        response_data = saltapi.task_create_api(tgt=tgt, tgt_type=tgt_type, arg=arg)
                        # 当调用api失败的时候会返回false
                        if response_data is False:
                            app_log.append('\nwindows创建计划任务后台出错_error(1)，请联系管理员')
                            result['result'] = app_log
                            return JsonResponse(result)
                        else:
                            try:
                                response_data = response_data['return'][0]
                                result['status'] = True
                                result['result'] = response_data
                                return JsonResponse(result)
                            except Exception as e:
                                app_log.append('\n' + 'windows创建计划任务失败_error(2):' + str(response_data))
                                result['result'] = app_log
                                return JsonResponse(result)
            elif request.GET.get('salt_tool_tag_key') == 'get_supervisor_content':
                program = request.GET.get('program')
                command = request.GET.get('command')
                directory = request.GET.get('directory')
                env = request.GET.get('env')
                logfile = request.GET.get('logfile')
                errorlogfile = request.GET.get('errorlogfile')
                arg = []
                arg.extend(['[program:%s]' % program, 'command=%s' % command, 'stdout_logfile_maxbytes=10MB',
                            'stderr_logfile_maxbytes=10MB', 'stdout_logfile_backups=5', 'stderr_logfile_backups=5',
                            'startsecs=5', 'stopsignal=QUIT', 'stopasgroup=true', 'killasgroup=true'])
                # 这是判断arg是否传输值过来，如果没有前端会传个['']过来，这是由于我前端设置了的
                if logfile != '':
                    arg.append('stdout_logfile=%s' % logfile)
                else:
                    logfile = 'stdout_logfile=/var/log/supervisor/%s.log' % program
                    arg.append(logfile)
                if errorlogfile != '':
                    arg.append('stderr_logfile=%s' % errorlogfile)
                else:
                    errorlogfile = 'stderr_logfile=/var/log/supervisor/%s.log' % program
                    arg.append(errorlogfile)
                if env != '':
                    arg.append('environment=%s' % env)
                if directory != '':
                    arg.append('directory=%s' % directory)
                result['status'] = True
                result['result'] = arg
                return JsonResponse(result)
            elif request.POST.get('salt_tool_tag_key') == 'create_supervisor':
                tgt = request.POST.get('tgt')
                tgt_type = request.POST.get('tgt_type')
                program = request.POST.get('program')
                command = request.POST.get('command')
                directory = request.POST.get('directory')
                env = request.POST.get('env')
                logfile = request.POST.get('logfile')
                errorlogfile = request.POST.get('errorlogfile')
                force = request.POST.get('force')
                # path文件存放的目录必须是supervisord.conf的include定义好的，所以无法自定义，只能内置
                path = '/etc/supervisord.d/'
                # file_path是文件路径加文件名后缀是.ini，这个也是在supervisord.conf的include定义好的格式
                file_path = path + program + '.ini'
                arg = []
                arg.extend(['[program:%s]' % program, 'command=%s' % command,'stdout_logfile_maxbytes=10MB',
                            'stderr_logfile_maxbytes=10MB', 'stdout_logfile_backups=5', 'stderr_logfile_backups=5',
                            'startsecs=5', 'stopsignal=QUIT', 'stopasgroup=true', 'killasgroup=true'])
                # 这是判断arg是否传输值过来，如果没有前端会传个['']过来，这是由于我前端设置了的
                if logfile != '':
                    logfile_path = logfile
                    arg.append('stdout_logfile=%s' % logfile_path)
                else:
                    logfile_path = '/var/log/supervisor/%s.log' % program
                    arg.append('stdout_logfile=%s' % logfile_path)
                if errorlogfile != '':
                    errorlogfile_path = errorlogfile
                    arg.append('stderr_logfile=%s' % errorlogfile_path)
                else:
                    errorlogfile_path = '/var/log/supervisor/%s.log' % program
                    arg.append('stderr_logfile=%s' % errorlogfile_path)
                if env != '':
                    arg.append('environment=%s' % env)
                if directory != '':
                    arg.append('directory=%s' % directory)
                with requests.Session() as s:
                    saltapi = SaltAPI(session=s)
                    if saltapi.get_token() is False:
                        app_log.append('\n创建supervisor进程后台出错_error(0)，请联系管理员')
                        result['result'] = app_log
                        return JsonResponse(result)
                    else:
                        response_data = saltapi.file_exists_api(tgt=tgt, tgt_type=tgt_type, arg=file_path)
                        # 当调用api失败的时候会返回false
                        if response_data is False:
                            app_log.append('\n创建supervisor进程后台出错_error(1)，请联系管理员')
                            result['result'] = app_log
                            return JsonResponse(result)
                        else:
                            try:
                                response_data = response_data['return'][0]
                                success_tgt = []
                                for k, v in response_data.items():
                                    # 判断如果执行的minion中是否已经存在了该文件夹，如果存在并且强制没有选中True就不继续执行这个minion的下一步操作
                                    if v is True and force == 'false':
                                        app_log.append({k: 'minion_id:%s已存在同名文件，如需覆盖请选择强制' % k})
                                    else:
                                        success_tgt.append(k)
                                if success_tgt:
                                    success_tgt = ','.join(success_tgt)
                                    response_data = saltapi.file_write_api(tgt=success_tgt, tgt_type='list', arg=[file_path, 'args=%s' % arg])
                                    if response_data is False:
                                        app_log.append('\n创建supervisor进程后台出错_error(2)，请联系管理员')
                                        result['result'] = app_log
                                        return JsonResponse(result)
                                    else:
                                        response_data = response_data['return']
                                        app_log.extend(response_data)
                                    # 日志文件目录创建
                                    response_data = saltapi.file_makedirs_api(tgt=success_tgt, tgt_type='list',
                                                                              arg=logfile_path)
                                    if response_data is False:
                                        app_log.append('\n创建supervisor进程日志创建出错_error(3)，请联系管理员')
                                        result['result'] = app_log
                                        return JsonResponse(result)
                                    response_data = saltapi.file_makedirs_api(tgt=success_tgt, tgt_type='list',
                                                                              arg=errorlogfile_path)
                                    if response_data is False:
                                        app_log.append('\n创建supervisor进程日志创建出错_error(4)，请联系管理员')
                                        result['result'] = app_log
                                        return JsonResponse(result)
                                    # 重载supervisord配置
                                    response_data = saltapi.supervisord_update_api(tgt=success_tgt, tgt_type='list')
                                    if response_data is False:
                                        app_log.append('\n创建supervisor进程重载配置出错_error(5)，请联系管理员')
                                        result['result'] = app_log
                                        return JsonResponse(result)
                                result['status'] = True
                                result['result'] = app_log
                                return JsonResponse(result)
                            except Exception as e:
                                app_log.append('\n' + '创建supervisor进程失败_error(3):' + str(response_data))
                                result['result'] = app_log
                                return JsonResponse(result)
            else:
                result['result'] = 'salt工具页ajax提交了错误的tag'
                return JsonResponse(result)
    except Exception as e:
        logger.error('salt命令执行ajax提交处理有问题', e)
        result['result'] = 'salt命令执行ajax提交处理有问题'
        return JsonResponse(result)
