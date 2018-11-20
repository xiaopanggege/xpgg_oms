#!/usr/bin/env python3
# -.- coding:utf-8 -.-

from django.shortcuts import render
from django.http import JsonResponse
import time
from xpgg_oms.forms import *
from xpgg_oms.models import *
from xpgg_oms.salt_api import SaltAPI
import requests
# 下面这个是py3解决requests请求https误报问题
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


import logging
# Create your views here.
logger = logging.getLogger('xpgg_oms.views')


# nginx管理
def nginx_manage(request):
    try:
        if request.method == 'GET':
            nginx_list = NginxManage.objects.all()
            return render(request, 'nginx/nginx_manage.html', {'nginx_list': nginx_list})
        else:
            nginx_ip = request.POST.get('nginx_ip')
            nginx_vip = request.POST.get('nginx_vip')
            nginx_path = request.POST.get('nginx_path')
            nginxconf_path = request.POST.get('nginxconf_path')
            nginxvhosts_path = request.POST.get('nginxvhosts_path')
            nginxlogs_path = request.POST.get('nginxlogs_path')
            # 判断nginx管理表是否已经存在此IP了，存在就不添加
            if NginxManage.objects.filter(ip=nginx_ip):
                response_data = {'result': 'IP:%s已存在nginx管理中' % nginx_ip, 'status': False}
                return JsonResponse(response_data)
            # 判断ip是否在minion列表里如果不在返回拒绝添加，因为必须用salt来控制，这里还有一个点就是minion的状态离线问题不知道要不要判断
            if MinionList.objects.filter(ip=nginx_ip):
                minion_id = MinionList.objects.get(ip=nginx_ip).minion_id
                NginxManage.objects.create(ip=nginx_ip, vip=nginx_vip, path=nginx_path, conf_path=nginxconf_path,
                                           vhost_path=nginxvhosts_path, logs_path=nginxlogs_path, update_time=time.strftime('%Y-%m-%d %X'),
                                           minion_id=minion_id)
                response_data = {'result': '新增nginx成功', 'status': True}
                return JsonResponse(response_data)
            else:
                response_data = {'result': 'IP:%s未安装salt-minion，请安装salt-minion并加入SaltKey' % nginx_ip, 'status': False}
                return JsonResponse(response_data)
    except Exception as e:
        logger.error('nginx管理问题', e)


# nginx配置文件列表
def nginx_conflist(request):
    try:
        if request.method == 'GET':
            minionid = request.GET.get('minionid')
            nginxconfpaht = request.GET.get('confpath')
            nginxvhostpaht = request.GET.get('vhostspath')
            nginxip = request.GET.get('nginxip')
            with requests.Session() as s:
                try:
                    token = s.post('http://192.168.68.50:8080/login',
                                   json={'username': 'saltapi', 'password': '123456', 'eauth': 'pam',})
                    token.raise_for_status()
                except Exception as e:
                    print('nginx配置文件列表获取token报错：', e)
                    return render(request, 'nginx/nginx_conflist.html')
                else:
                    data = {'client': 'local',
                            'tgt': minionid,
                            'expr_form': 'glob',
                            'fun': 'cmd.run',
                            'arg': 'ls -A %s/*.conf %s/*.conf %s/.*.swp %s/.*.swp' % (nginxconfpaht, nginxvhostpaht, nginxconfpaht, nginxvhostpaht),
                            }
                    try:
                        response_data = s.post('http://192.168.68.50:8080', data=data)
                        response_data.raise_for_status()
                    except Exception as e:
                        print(e)
                        # logger.error(e)
                        # return logger.info(e + ' 无法获取数据')
                        return render(request, 'nginx/nginx_conflist.html')
                    else:
                        data = response_data.json()['return'][0][minionid]
                        datalist = data.split('\n')
                        # 获得配置文件列表（带绝对路径的），并且把没有查找到的排除掉No such file or directory
                        datalist = [x for x in datalist if 'No such file or directory' not in x]
                        # 筛选出conf文件排除掉swp文件
                        conf_list = [x for x in datalist if x[-4:] != '.swp']
                        # 因为conf文件有可能正在被人编辑，那么我们就无法操作不然会冲突，所以需要判断swp是否存在，swp就是在编辑时候的缓存文件
                        swp_list = [x for x in datalist if x[-4:] == '.swp']
                        conflist = []
                        # 循环conf文件列表判断是否有同名swp文件，如果有就在4元祖最后一个内容改成'正在编辑中'
                        for x in conf_list:
                            for y in swp_list:
                                if x.rsplit('/', 1)[1] == y.rsplit('/', 1)[1][1:-4]:
                                    conflist.append((x, x.rsplit('/', 1)[1], x.rsplit('/', 1)[0], '正在被编辑中'))
                                    break
                            else:
                                # 获得配置文件名，3元祖为了好给前端直接使用，第一个是类似/tmp/nginx.conf，第二个是nginx.conf，三个是/tmp,第四个是判断是否在编辑
                                conflist.append((x, x.rsplit('/', 1)[1], x.rsplit('/', 1)[0], '正常'))

                        # conflist = [(x, x.rsplit('/', 1)[1], x.rsplit('/', 1)[0]) for x in datalist]
                        return render(request, 'nginx/nginx_conflist.html', {'conflist': conflist, 'minionid':minionid, 'nginxip':nginxip})
    except Exception as e:
        logger.error('miniion管理页面有问题', e)
        return render(request, 'nginx/nginx_conflist.html')


# 做一个nginx切换负载的小功能，作为nginx管理后台的起步
def nginx_upstream(request):
    reg1 = re.compile(r'\nupstream[^\}]+}')
    reg2 = re.compile(r'\nupstream[^\{]+')
    reg3 = re.compile(r'\#* *server \d[^;]+;')
    reg4 = re.compile(r'\#+ *')
    upstreamlist = []
    try:
        if request.method == 'GET':
            minionid = request.GET.get('minionid')
            nginxip = request.GET.get('nginxip')
            path = request.GET.get('path')
            with requests.Session() as s:
                saltapi = SaltAPI(session=s)
                if saltapi.get_token() is False:
                    logger.error('nginx_upstream页get操作获取SaltAPI调用get_token请求出错')
                    return render(request, 'nginx/nginx_upstream.html')
                else:
                    response_data = saltapi.cmd_run_api(tgt=minionid, arg='cat %s' % path)
                    if response_data is False:
                        logger.error('获取upstream列表失败可能代入的参数有问题，SaltAPI调用cmd_run_api请求出错')
                        return render(request, 'nginx/nginx_upstream.html')
                    # 判断upstream_data如果返回值如果为[{}]表明没有这个minionid
                    elif response_data['return'] != [{}]:
                        data_source = response_data['return'][0][minionid]
                        data_list = re.findall(reg1, data_source)
                        for i in data_list:
                            # 获取upstream name
                            b2 = re.search(reg2, i)
                            # 获取upstream server列表
                            b3 = re.findall(reg3, i)
                            # 用空格切割字符串取第二个就是servername了
                            namekey = b2.group().split(' ')[1]
                            # 下面这个如果直接赋值b3会有一些问题，就是出现'##  server'这样的也会被前端输出，所以用了
                            # 正则把这种出现'###  '是全部替换成#这样不仅显示正常，在下面post中获取的前端upstream_server也会正确，很重要
                            upstreamlist.append([namekey, [re.sub(reg4, '#', x.strip()) for x in b3]])
                        return render(request, 'nginx/nginx_upstream.html',
                                      {'upstreamlist': upstreamlist, 'minionid': minionid, 'nginxip': nginxip, 'path': path})
                    else:
                        logger.error('获取upstream列表失败，请确认minion是否存在。。')
                        return render(request, 'nginx/nginx_upstream.html')
        # 切换里面server的up/down状态，其实就是注释加#和不注释而已
        else:
            upstream_name = request.POST.get('upstream_name')
            upstream_server = request.POST.get('upstream_server')
            upstream_status = request.POST.get('upstream_status')
            minionid = request.POST.get('minionid')
            path = request.POST.get('path')
            with requests.Session() as s:
                saltapi = SaltAPI(session=s)
                if saltapi.get_token() is False:
                    logger.error('nginx_upstream页状态变更操作获取SaltAPI调用get_token请求出错')
                    return JsonResponse({'result': '失败,后台问题', 'status': False})
                else:
                    if upstream_status == 'down':
                        arg = "sed -i '/^upstream *%s/,/^}$/{s/%s/#%s/g}' %s&&free -m" % (upstream_name, upstream_server, upstream_server, path)
                    else:
                        arg = "sed -i '/^upstream *%s/,/^}$/{s/#\+ *%s/%s/g}' %s&&free -m" % (upstream_name, upstream_server, upstream_server, path)
                    response_data = saltapi.cmd_run_api(tgt=minionid, arg=arg)
                    if response_data is False:
                        logger.error('nginx_upstream页状态变更SaltAPI调用cmd_run_api请求出错')
                        return JsonResponse({'result': '失败,后台问题', 'status': False})
                    # 返回值如果为[{}]表明没有这个minionid
                    elif response_data['return'] == [{}]:
                        logger.error('nginx_upstream页状态变更SaltAPI调用cmd_run_api获取到空值了')
                        return JsonResponse({'result': '失败,后台问题', 'status': False})
                    else:
                        return JsonResponse({'result': '成功', 'status': True})
    except Exception as e:
        logger.error('获取upstream列表失败'+str(e))
        return render(request, 'nginx/nginx_upstream.html')


# nginx的upstream负载切换页面新增一个server功能
def nginx_upstreamserver_add(request):
    minionid = request.POST.get('minionid')
    path = request.POST.get('path')
    upserverdata = request.POST.get('upserverdata')
    upstreamname = request.POST.get('upstreamname')
    srserver = request.POST.get('srserver')
    with requests.Session() as s:
        try:
            token = s.post('http://192.168.68.50:8080/login',
                           json={'username': 'saltapi', 'password': '123456', 'eauth': 'pam', })
            token.raise_for_status()
        except Exception as e:
            logger.error('upstream新增server操作post获取token报错：'+str(e))
            return JsonResponse({'result': 'upstream新增server操作post获取token报错', 'status': False})
        else:
            serverdata = 'server '+upserverdata+';'
            # 注意下面的命令和在shell下执行不一样地方就是\\n\\t在shell下直接\n\t，在这里之所以要这样因为不转义为普通的\n\t会直接先被
            # python给解析掉了。。。直接变成回车和tab了，无法传到客户端去，无语，坑啊，记住了！！！
            arg = "sed -i '/^upstream *%s/,/^}$/{s/%s/%s\\n\\t%s/g}' %s" % (upstreamname, srserver, srserver, serverdata, path)
            data = {'client': 'local',
                    'tgt': minionid,
                    'tgt_type': 'glob',
                    'fun': 'cmd.run',
                    'arg': arg,
                    }
            try:
                response_data = s.post('http://192.168.68.50:8080', data=data)
                response_data.raise_for_status()
            except Exception as e:
                reponse_data = '新增upstream的server配置操作提交出错：'
                logger.error(reponse_data + str(e))
                # return logger.info(e + ' 无法获取数据')
                return JsonResponse({'result': '失败', 'status': False})
            else:
                logger.error(response_data.json())
                return JsonResponse({'result': '成功', 'status': True})


# nginx reload操作,也是在nginx负载切换的页面。由于是ajax提交所以可以分开单独写呵呵
def nginx_reload(request):
    minionid = request.POST.get('minionid')
    nginxip = request.POST.get('nginxip')
    with requests.Session() as s:
        try:
            token = s.post('http://192.168.68.50:8080/login',
                           json={'username': 'saltapi', 'password': '123456', 'eauth': 'pam',})
            token.raise_for_status()
        except Exception as e:
            logger.error('nginx reload操作post获取token报错：', e)
            return JsonResponse({'result': 'nginx reload操作post获取token报错', 'status': False})
        else:
            # 通过nginxip获取nginx的path和conf路径来reload
            nginx = NginxManage.objects.get(ip=nginxip)
            path = nginx.path
            conf = nginx.confpath
            cmd = '%ssbin/nginx -t -c %snginx.conf && %ssbin/nginx -s reload' % (path, conf, path)
            data = {'client': 'local',
                    'tgt': minionid,
                    'expr_form': 'glob',
                    'fun': 'cmd.run',
                    'arg': cmd,
                    }
            try:
                response_data = s.post('http://192.168.68.50:8080', data=data)
                response_data.raise_for_status()
            except Exception as e:
                reponse_data = 'nginx重载配置操作提交出错：'
                logger.error(reponse_data + str(e))
                # return logger.info(e + ' 无法获取数据')
                return JsonResponse({'result': '失败', 'status': False})
            else:
                data = response_data.json()['return'][0][minionid]
                if 'test is successful' in data:
                    return JsonResponse({'result': 'reload成功', 'status': True})
                else:
                    return JsonResponse({'result': data, 'status': False})