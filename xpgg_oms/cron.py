#!/usr/bin/env python3
#-.- coding=utf-8 -.-

import time
from .models import *
from . import views
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

import logging
logger = logging.getLogger('xpgg_oms.views')


# 旧版下面有新版
def minion_status_old():
    # 用values_list配合flat=True得到minionid的列表，good
    minion_list = MinionList.objects.values_list('minionid', flat=True)
    # 因为用values_list获取的确实是列表但是是QuerySet对象的列表，如果要执行append或者remove等list操作无法执行，刚好下面就需要执行，所以要list()转变成真的列表
    minion_list = list(minion_list)
    print('开始更新minion列表'+time.strftime('%Y-%m-%d %X'))
    with requests.Session() as s:
        try:
            token = s.post('http://192.168.68.50:8080/login',
                       json={'username': 'saltapi', 'password': '123456', 'eauth': 'pam', })
            token.raise_for_status()
        except Exception as e:
            print('获取token失败')
            # return logger.info(e + ' don\'t get token')
        else:
            #第一版通过salt-run manage.status获取到minon的id列表，但是在开发过程中发现一个问题，无法获取精确ip
            #用salt \* network.ipaddrs如果minon是多ip会获取多个ip出来，然后再去判断哪个才是正确和master通信的ip
            #这点很蛋疼，所以才有了第二版，也希望以后如果salt玩好了看有没更方便的方法获取正确IP
            # data = {'client': 'runner',
            #     'fun': 'manage.status',
            #     }
            # try:
            #     response_data = s.post('http://192.168.68.50:8080', data=data)
            #
            #     response_data.raise_for_status()
            #     # print(response_data.json())
            #     data_list = response_data.json()['return']
            #     #从返回的字典中获取up和down的值，值已经默认是列表了，比较方便
            #     up_list = data_list[0]['up']
            #     down_list = data_list[0]['down']
            # except Exception as e:
            #     print('获取minion状态失败')
            #     return '哈哈2'
            #     # return logger.info(e + '获取minion状态失败')

            #第二版，前提条件把master也加入到minion中，我这里id命名为master，然后通过ss命令获取和master的4505端口保持
            #连接的ip地址，通过ip地址来查找minion的配置，获取的ip地址就表示存在的minion，不知道这点上面还有没漏洞先用着
            data = {'client': 'local',
                    'tgt': '192.168.68.50-master',
                    'fun': 'cmd.run',
                    # 得到ip列表，有一个问题master的ip在列表会存在2次，所以后来我优化了下命令去重|sort| uniq先排序才能去重
                    'arg': "ss -antp | grep '192.168.68.50:4505' | grep 'ESTAB'| awk -F '[ :]+' '{print $6}'|sort| uniq",
                    }
            try:
                response_data = s.post('http://192.168.68.50:8080', data=data)
                response_data.raise_for_status()
            except Exception as e:
                print('获取和master连接的minon的ip数据状态失败',e)
            else:
                data_response = response_data.json()['return'][0]['192.168.68.50-master']
                ip_list = (data_response.split())
                try:
                    for mip in ip_list:
                        #遍历ip列表获取到我要的几个信息，这里只要了和系统版本以及minion版本相关的，实际上可以获取非常多哟
                        #所以这里留着如果需要获取更多数据的时候继续扩展
                        ipdata = {'client': 'local',
                                  'tgt': mip,
                                  'expr_form': 'ipcidr',
                                  'fun': 'grains.item',
                                  'arg': ['os', 'osrelease', 'saltversion'],
                                  }
                        try:
                            response_ipdata = s.post('http://192.168.68.50:8080', data=ipdata)
                            response_ipdata.raise_for_status()
                        except Exception as e:
                            print('获取minon数据失败', e)
                        else:
                            if response_ipdata.json()['return'] != [{}]:
                                minion_data = response_ipdata.json()['return'][0]
                                #通过下面的逻辑把我要的数据minion_id,os, saltversion提取出来
                                minion_id = list(minion_data.keys())[0]
                                values = list(minion_data.values())[0]
                                os, saltversion = values['os'] + values['osrelease'], values['saltversion']
                                #django1.7出了一个新方法update_or_create存在就更新不存在就创建，有空可以试下
                                #如果在数据库存在就更新，不存在就新建，更新的时候把更新的id从列表剔除，这样最后剩下的就是没更新到的，没更新到表明离线
                                if minion_id in minion_list:
                                    MinionList.objects.filter(minionid=minion_id).update(ip=mip,minionversion=saltversion,systemissue=os,minionstatus='在线',updatetime=time.strftime('%Y-%m-%d %X'))
                                    minion_list.remove(minion_id)
                                    print('更新minion数据成功')
                                else:
                                    MinionList.objects.create(minionid=minion_id,ip=mip, minionversion=saltversion,systemissue=os, minionstatus='在线',updatetime=time.strftime('%Y-%m-%d %X'))
                                    print('新增minion数据成功')
                    #把minion_list剩下的状态都改成离线，因为在线的就是上面更新或者新增的了
                    if minion_list:
                        for ii in minion_list:
                            MinionList.objects.filter(minionid=ii).update(minionstatus='离线',updatetime=time.strftime('%Y-%m-%d %X'))
                    print('minion列表更新完成'+time.strftime('%Y-%m-%d %X'))
                except Exception as e:
                    print('minion列表更新出错，请检查'+time.strftime('%Y-%m-%d %X'),e)



def saltkey_list():
    print('开始更新SaltKeyList表' + time.strftime('%Y年%m月%d日 %X'))
    salt_list = SaltKeyList.objects.values_list('minion_id', 'certification_status')
    minion_list = []
    with requests.Session() as s:
        saltapi = views.SaltAPI(session=s)
        if saltapi.get_token() is False:
            logger.error('saltkey_list定时操作获取SaltAPI调用get_token请求出错')
            print('saltkey_list定时操作获取SaltAPI调用get_token请求出错')
            return False
        else:
            response_data = saltapi.saltkey_listall_api()
            try:
                data_source = response_data['return'][0]['data']['return']
                minions_pre = data_source['minions_pre']
                minions_denied = data_source['minions_denied']
                minions = data_source['minions']
                minions_rejected = data_source['minions_rejected']
                if minions_pre:
                    for i in minions_pre:
                        minion_list.append((i, 'unaccepted'))
                        updated_values = {'minion_id': i, 'certification_status': 'unaccepted',
                                          'update_time': time.strftime('%Y年%m月%d日 %X')}
                        SaltKeyList.objects.update_or_create(minion_id=i, certification_status='unaccepted', defaults=updated_values)
                if minions_denied:
                    for i in minions_denied:
                        minion_list.append((i, 'denied'))
                        updated_values = {'minion_id': i, 'certification_status': 'denied',
                                          'update_time': time.strftime('%Y年%m月%d日 %X')}
                        SaltKeyList.objects.update_or_create(minion_id=i, certification_status='denied', defaults=updated_values)
                if minions:
                    for i in minions:
                        minion_list.append((i, 'accepted'))
                        updated_values = {'minion_id': i, 'certification_status': 'accepted',
                                          'update_time': time.strftime('%Y年%m月%d日 %X')}
                        SaltKeyList.objects.update_or_create(minion_id=i, certification_status='accepted', defaults=updated_values)
                if minions_rejected:
                    for i in minions_rejected:
                        minion_list.append((i, 'rejected'))
                        updated_values = {'minion_id': i, 'certification_status': 'rejected',
                                          'update_time': time.strftime('%Y年%m月%d日 %X')}
                        SaltKeyList.objects.update_or_create(minion_id=i, certification_status='rejected', defaults=updated_values)
                # 删除原表中不在本次查询结果里的记录，因为如果你删除了一个minion那么查询结果就没有这个minion了所以要从表中删除
                for i in salt_list:
                    if i not in minion_list:
                        SaltKeyList.objects.filter(minion_id=i[0], certification_status=i[1]).delete()
                print('saltkey_list表更新完成' + time.strftime('%Y年%m月%d日 %X'))
                return True
            except Exception as e:
                logger.error('saltkey_list在执行数据库操作时候出错了：' + str(e))
                print('saltkey_list表更新出错，请检查' + time.strftime('%Y年%m月%d日 %X'), e)
                return False


# 更新minion再次改变，这个弃用，原因是salt-run manage.alive不适用有nat转换后全是同一个外网ip的minion
def old2_minion_status():
    # 用values_list配合flat=True得到minion_id的列表，用values_list获取的不是列表是QuerySet对象
    # 如果要执行append或者remove等list操作无法执行
    minion_list = MinionList.objects.values_list('minion_id', flat=True)
    id_list = []
    print('开始更新Minion列表'+time.strftime('%Y年%m月%d日 %X'))
    with requests.Session() as s:
        saltapi = views.SaltAPI(session=s)
        if saltapi.get_token() is False:
            logger.error('minion_status定时操作获取SaltAPI调用get_token请求出错')
            print('minion_status定时操作获取SaltAPI调用get_token请求出错')
            return False
        else:
            # salt检测minion最快的方法，不访问minion而是直接通过和端口4505保持连接的ip来检测，和我旧版手动写功能一样，官方也出了
            # 目前这个方法有个不算BUG的BUG就是环境必须是内网，如果出现用nat端口转发则因为这个命令本身获取是master的端口连接装态通过
            # nat过来的连接ip都会是一个nat出口ip，导致判断错误，所以如果确认都是内网环境才可以使用
            online_data = saltapi.saltrun_manage_alive_api(arg='show_ipv4=True')
            if online_data is False:
                print('saltrun_manage_alive_api调用API失败了')
                return False
            elif online_data['return'] == [[]]:
                print('没有在线的minion，搞笑')
            else:
                try:
                    id_list.extend([key for key in online_data['return'][0]])
                    grains_data = saltapi.grains_itmes_api(tgt=id_list, tgt_type='list')
                    # 这里获取了所有minion的grains内容，如果以后表字段有增加就从这里取方便
                    for key, value in grains_data['return'][0].items():
                        minion_id = key
                        ip = online_data['return'][0][key]
                        os = value['os'] + value['osrelease']
                        saltversion = value['saltversion']
                        sn = value['serialnumber']
                        cpu_num = value['num_cpus']
                        cpu_model = value['cpu_model']
                        sys = value['kernel']
                        kernel = value['kernelrelease']
                        productname = value['productname']
                        ipv4_addr = value['ip4_interfaces']
                        mac_addr = value['hwaddr_interfaces']
                        localhost = value['localhost']
                        mem_total = value['mem_total']
                        updated_values = {'minion_id': minion_id, 'minionstatus': '在线', 'ip': ip, 'sn': sn,
                                          'cpu_num': cpu_num, 'cpu_model': cpu_model, 'sys': sys, 'kernel': kernel,
                                          'productname': productname, 'ipv4_addr': ipv4_addr, 'mac_addr': mac_addr,
                                          'localhost': localhost, 'mem_total': mem_total,
                                          'minionversion': saltversion, 'systemissue': os,
                                          'updatetime': time.strftime('%Y年%m月%d日 %X')}
                        MinionList.objects.update_or_create(minion_id=key, defaults=updated_values)
                except Exception as e:
                    print('minion列表更新在线数据出错1，请检查'+time.strftime('%Y年%m月%d日 %X'), e)
                    return False
            offline_data = saltapi.saltrun_manage_notalive_api()
            if offline_data is False:
                print('saltrun_manage_notalive_api调用API失败了')
                return False
            elif offline_data['return'] == [[]]:
                print('恭喜有没离线的minion')
            else:
                try:
                    # 获取不在线结果的结构是这样的：{'return': [['10.10.10.100', '10.10.10.116']]}
                    for key in offline_data['return'][0]:
                        id_list.append(key)
                        updated_values = {'minion_id': key, 'minionstatus': '离线',
                                          'updatetime': time.strftime('%Y年%m月%d日 %X')}
                        MinionList.objects.update_or_create(minion_id=key, defaults=updated_values)
                except Exception as e:
                    print('minion列表更新离线数据出错2，请检查' + time.strftime('%Y年%m月%d日 %X'), e)
                    return False
            # 清理表中多出来的条目
            try:
                for i in minion_list:
                    if i not in id_list:
                        MinionList.objects.filter(minion_id=i).delete()
                print('minion列表更新完成' + time.strftime('%Y年%m月%d日 %X'))
                return True
            except Exception as e:
                print('minion列表更新出错，请检查' + time.strftime('%Y年%m月%d日 %X'), e)
                return False


def minion_status():
    # 用values_list配合flat=True得到minion_id的列表，用values_list获取的不是列表是QuerySet对象
    # 如果要执行append或者remove等list操作无法执行
    minion_list = MinionList.objects.values_list('minion_id', flat=True)
    id_list = []
    print('开始更新Minion列表'+time.strftime('%Y年%m月%d日 %X'))
    with requests.Session() as s:
        saltapi = views.SaltAPI(session=s)
        if saltapi.get_token() is False:
            logger.error('minion_status定时操作获取SaltAPI调用get_token请求出错')
            print('minion_status定时操作获取SaltAPI调用get_token请求出错')
            return False
        else:
            # salt检测minion最准的方法salt-run manage.status
            minion_data = saltapi.saltrun_manage_status_api()
            if minion_data is False:
                print('saltrun_manage_status_api调用API失败了')
                return False
            else:
                try:
                    id_list.extend(minion_data['return'][0]['up'])
                    grains_data = saltapi.grains_itmes_api(tgt=id_list, tgt_type='list')
                    # 这里获取了所有minion的grains内容，如果以后表字段有增加就从这里取方便
                    for key, value in grains_data['return'][0].items():
                        minion_id = key
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
                            updated_values = {'minion_id': key, 'minion_status': '异常',
                                              'update_time': time.strftime('%Y年%m月%d日 %X')}
                            MinionList.objects.update_or_create(minion_id=key, defaults=updated_values)
                        else:
                            updated_values = {'minion_id': minion_id, 'minion_status': '在线', 'ip': ip, 'sn': sn,
                                              'cpu_num': cpu_num, 'cpu_model': cpu_model, 'sys': sys, 'kernel': kernel,
                                              'product_name': productname, 'ipv4_address': ipv4_addr, 'mac_address': mac_addr,
                                              'localhost': localhost, 'mem_total': mem_total,
                                              'minion_version': saltversion, 'system_issue': os,
                                              'update_time': time.strftime('%Y年%m月%d日 %X')}
                            MinionList.objects.update_or_create(minion_id=key, defaults=updated_values)
                except Exception as e:
                    print('minion列表更新在线数据出错1，请检查'+time.strftime('%Y年%m月%d日 %X'), e)
                    return False
                try:
                    # 更新离线minion状态
                    for key in minion_data['return'][0]['down']:
                        id_list.append(key)
                        updated_values = {'minion_id': key, 'minion_status': '离线',
                                          'update_time': time.strftime('%Y年%m月%d日 %X')}
                        MinionList.objects.update_or_create(minion_id=key, defaults=updated_values)
                except Exception as e:
                    print('minion列表更新离线数据出错2，请检查' + time.strftime('%Y年%m月%d日 %X'), e)
                    return False
            # 清理表中多出来的条目
            try:
                for i in minion_list:
                    if i not in id_list:
                        MinionList.objects.filter(minion_id=i).delete()

                        # 下面这些本来是用来操作清理minion表后一些关联了minion的业务表也删除，但是后面想想我不动声响的后台去删除这些
                        # 表中的数据，对于使用人来说是很坑爹的事情，等下人家都不知道怎么minion就消失了，然后可能还会忘了到底原来是关联
                        # 那一个minion_id的，所以最后想了想还是不删除；业务逻辑中写判断minion是否存在，这样还有一个问题就是如果minion
                        # 清理后再重新添加回来，假设加回来的是另一台服务器那会造成业务系统之前绑定了这个minion的在操作的时候会操作错误
                        # 因为minion实际的后端服务器换了一台，所以要在规范上面来避免这问题，尽量小心删除salt-key操作，检查是否有关联
                        # 业务，或者后期看下需不需要下面的删除操作改成类似添加备注说明下被删除了

                        # # 对AppRelease中的minion_id做删除操作，因为这个表关联了minion表，不过我没用外键，所以要手动来
                        # # 下面是用正则匹配minion_id只有一个或者多个时候在前面在中间在最后的情况
                        # app_data_list = AppRelease.objects.filter(
                        #     minion_id__regex=r'^%s$|^%s,|,%s$|,%s,' % (i, i, i, i))
                        # for app_data in app_data_list:
                        #     app_name = app_data.app_name
                        #     minion_id = app_data.minion_id
                        #     minion_id = minion_id.split(',')
                        #     minion_id.remove(i)
                        #     minion_id = ','.join(minion_id)
                        #     AppRelease.objects.filter(app_name=app_name).update(minion_id=minion_id)
                print('minion列表更新完成' + time.strftime('%Y年%m月%d日 %X'))
                return True
            except Exception as e:
                logger.error('minion列表更新出错，请检查' + time.strftime('%Y年%m月%d日 %X')+str(e))
                print('minion列表更新出错，请检查' + time.strftime('%Y年%m月%d日 %X'), e)
                return False