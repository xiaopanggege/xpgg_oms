#!/usr/bin/env python3
# -.- coding:utf-8 -.-

from django.shortcuts import render
import json
from django.http import JsonResponse
import time
from xpgg_oms.forms import *
from xpgg_oms.models import *
from xpgg_oms.salt_api import SaltAPI
from django.conf import settings
import requests
# 下面这个是py3解决requests请求https误报问题
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from .v_general import getPage
from .v_saltstack import format_state

import logging
# Create your views here.
logger = logging.getLogger('xpgg_oms.views')


# H5临时发布系统
def h5_issue(request):
    return render(request, 'release_sys/h5_issue.html')


# H5——svn检出
def h5_svn_co(request):
    svn_addr = request.POST.get('svn_addr')
    svn_user = request.POST.get('svn_user')
    svn_pwd = request.POST.get('svn_pwd')
    svn_version = request.POST.get('svn_version')
    local_path = '/data/svn/'+svn_addr.rsplit('/', 1)[1]
    minionid='192.168.68.50-master'
    with requests.Session() as s:
        saltapi = SaltAPI(session=s)
        if saltapi.get_token() is False:
            logger.error('h5_svn检出获取SaltAPI调用get_token请求出错')
            return JsonResponse({'result': 'h5_svn检出获取SaltAPI调用get_token请求出错', 'status': False})
        else:
            response_data = saltapi.cmd_run_api(tgt=minionid, arg=['cd %s && svn up -r %s --non-interactive  --username=%s --password=%s ' % (local_path, svn_version, svn_user, svn_pwd), 'reset_system_locale=false'])
            if response_data is False:
                logger.error('h5_svn检出可能代入的参数有问题，SaltAPI调用cmd_run_api请求出错')
                return JsonResponse({'result': 'h5_svn检出可能代入的参数有问题，SaltAPI调用cmd_run_api请求出错', 'status': False})
            # 判断upstream_data如果返回值如果为[{}]表明没有这个minionid
            elif response_data['return'] != [{}]:
                data_source = response_data['return'][0][minionid]
                logger.error(data_source)
                if 'svn: E' in data_source:
                    return JsonResponse({'result': data_source, 'status': False})
                # 在首次更新的时候如果还没做过svn co检出是无法更新的，所以要判断是否已经存在了这个svn目录，不存在就要co一次
                elif 'No such file or directory' in data_source:
                    response_data = saltapi.cmd_run_api(tgt=minionid, arg=['svn co -r %s --non-interactive %s %s --username=%s --password=%s' % (svn_version, svn_addr, local_path, svn_user, svn_pwd), 'reset_system_locale=false'])
                    if response_data is False:
                        logger.error('h5_svn检出可能代入的参数有问题，SaltAPI调用cmd_run_api请求出错')
                        return JsonResponse({'result': 'h5_svn检出可能代入的参数有问题，SaltAPI调用cmd_run_api请求出错', 'status': False})
                    # 判断upstream_data如果返回值如果为[{}]表明没有这个minionid
                    elif response_data['return'] != [{}]:
                        data_source = response_data['return'][0][minionid]
                        if 'svn: E' in data_source:
                            return JsonResponse({'result': data_source, 'status': False})
                        else:
                            return JsonResponse({'result': data_source, 'status': True})
                    else:
                        logger.error('h5_svn检出失败，请确认minion是否存在。。')
                        return JsonResponse({'result': 'h5_svn检出失败，请确认minion是否存在。。', 'status': False})
                else:
                    return JsonResponse({'result': data_source, 'status': True})
            else:
                logger.error('h5_svn检出失败，请确认minion是否存在。。')
                return JsonResponse({'result': 'h5_svn检出失败，请确认minion是否存在。。', 'status': False})


# H5——svn压缩
def h5_svn_zip(request):
    svn_addr = request.POST.get('svn_addr')
    cwd = '/data/svn/'+svn_addr.rsplit('/', 1)[1]
    zip_path = request.POST.get('zip_path')
    minionid='192.168.68.50-master'
    with requests.Session() as s:
        saltapi = SaltAPI(session=s)
        if saltapi.get_token() is False:
            logger.error('h5_svn压缩获取SaltAPI调用get_token请求出错')
            return JsonResponse({'result': 'h5_svn压缩获取SaltAPI调用get_token请求出错', 'status': False})
        else:
            response_data = saltapi.cmd_run_api(tgt=minionid, arg='tar -C %s -cvf %s *' % (cwd, zip_path))
            if response_data is False:
                logger.error('h5_svn压缩获取可能代入的参数有问题，SaltAPI调用cmd_run_api请求出错')
                return JsonResponse({'result': 'h5_svn检出可能代入的参数有问题，SaltAPI调用cmd_run_api请求出错', 'status': False})
            # 判断upstream_data如果返回值如果为[{}]表明没有这个minionid
            elif response_data['return'] != [{}]:
                data_source = response_data['return'][0][minionid]
                return JsonResponse({'result': data_source, 'status': True})
            else:
                logger.error('h5_svn压缩获取失败，请确认minion是否存在。。')
                return JsonResponse({'result': 'h5_svn压缩获取，请确认minion是否存在。。', 'status': False})


# H5压缩文件查询，用来部署前选择部署文件
def h5_file(request):
    project_file = request.POST.get('project_file')
    minionid = '192.168.68.50-master'
    if project_file == 'H5_*.tar':
        with requests.Session() as s:
            saltapi = SaltAPI(session=s)
            if saltapi.get_token() is False:
                logger.error('h5_file获取SaltAPI调用get_token请求出错')
                return JsonResponse({'result': 'h5_file获取SaltAPI调用get_token请求出错', 'status': False})
            else:
                # 第一个要在master中定义好，第二个zip_path是minion的路径，解压可以解压到一个不存在的目录，会自动创建哟
                response_data = saltapi.cmd_run_api(tgt=minionid,
                                                    arg="find /data/svnzip/ -type f -name '%s' | xargs ls -t" % project_file)
                if response_data is False:
                    logger.error('h5_file可能代入的参数有问题，SaltAPI调用archive_unzip_api请求出错')
                    return JsonResponse(
                        {'result': 'h5_file可能代入的参数有问题，SaltAPI调用archive_unzip_api请求出错', 'status': False})
                # 判断upstream_data如果返回值如果为[{}]表明没有这个minionid
                elif response_data['return'] != [{}]:
                    data_source = response_data['return'][0][minionid]
                    data_source = [x.split('/')[-1] for x in data_source.split()]
                    return JsonResponse({'result': data_source, 'status': True})
                else:
                    logger.error('h5_file失败，请确认minion是否存在。。')
                return JsonResponse({'result': 'h5_file失败，请确认minion是否存在。。', 'status': False})


# H5-svn文件传输
def h5_svn_push(request):
    zip_file = request.POST.get('project_file')
    zip_path = '/data/svnzip/'+zip_file
    source_path = 'salt://%s?saltenv=svnzip' % zip_file
    # 下面这个到时候改成H5的minionid
    project_ip = request.POST.get('project_ip')
    minion_id = MinionList.objects.get(ip=project_ip).minion_id
    with requests.Session() as s:
        saltapi = SaltAPI(session=s)
        if saltapi.get_token() is False:
            logger.error('h5_svn推送获取SaltAPI调用get_token请求出错')
            return JsonResponse({'result': 'h5_svn推送获取SaltAPI调用get_token请求出错', 'status': False})
        else:
            # 第一个要在master中定义好，第二个zip_path是minion的路径
            response_data = saltapi.cp_get_file_api(tgt=minion_id, arg=[source_path, zip_path])
            if response_data is False:
                logger.error('h5_svn推送可能代入的参数有问题，SaltAPI调用cp_get_file_api请求出错')
                return JsonResponse({'result': 'h5_svn推送可能代入的参数有问题，SaltAPI调用cp_get_file_api请求出错', 'status': False})
            # 判断upstream_data如果返回值如果为[{}]表明没有这个minionid
            elif response_data['return'] != [{}]:
                data_source = response_data['return'][0][minion_id]
                return JsonResponse({'result': data_source, 'status': True})
            else:
                logger.error('h5_svn推送失败，请确认minion是否存在。。')
                return JsonResponse({'result': 'h5_svn推送失败，请确认minion是否存在。。', 'status': False})


# H5-svn文件解压
def h5_svn_unzip(request):
    zip_file = request.POST.get('project_file')
    zip_path = '/data/svnzip/' + zip_file
    project_addr = request.POST.get('project_addr')
    # 下面这个到时候改成H5的minionid
    project_ip = request.POST.get('project_ip')
    minion_id = MinionList.objects.get(ip=project_ip).minion_id
    with requests.Session() as s:
        saltapi = SaltAPI(session=s)
        if saltapi.get_token() is False:
            logger.error('h5_svn解压获取SaltAPI调用get_token请求出错')
            return JsonResponse({'result': 'h5_svn解压获取SaltAPI调用get_token请求出错', 'status': False})
        else:
            # 第一个要在master中定义好，第二个是minion的路径，解压可以解压到一个不存在的目录，会自动创建哟
            response_data = saltapi.cmd_run_api(tgt=minion_id, arg='tar -xvf %s -C %s' % (zip_path, project_addr))
            if response_data is False:
                logger.error('h5_svn解压可能代入的参数有问题，SaltAPI调用archive_unzip_api请求出错')
                return JsonResponse({'result': 'h5_svn解压可能代入的参数有问题，SaltAPI调用archive_unzip_api请求出错', 'status': False})
            # 判断upstream_data如果返回值如果为[{}]表明没有这个minionid
            elif response_data['return'] != [{}]:
                data_source = response_data['return'][0][minion_id]
                logger.error(data_source)
                return JsonResponse({'result': data_source, 'status': True})
            else:
                logger.error('h5_svn解压失败，请确认minion是否存在。。')
                return JsonResponse({'result': 'h5_svn解压失败，请确认minion是否存在。。', 'status': False})


# 发布系统 应用发布 主
def app_release(request):
    try:
        if request.method == 'GET':
            # 默认如果没有get到的话值为None，这里我需要为空''，所以下面修改默认值为''
            search_field = request.GET.get('search_field', '')
            search_content = request.GET.get('search_content', '')
            # 判断是否为超级管理员或者普通用户，按权限分配
            if request.user.is_superuser:
                if search_content is '':
                    app_data = AppRelease.objects.all().order_by('create_time')
                    data_list = getPage(request, app_data, 15)
                else:
                    if search_field == 'search_app_name':
                        app_data = AppRelease.objects.filter(
                            app_name__icontains=search_content).order_by(
                            'create_time')
                        data_list = getPage(request, app_data, 15)
                    elif search_field == 'search_minion_id':
                        app_data = AppRelease.objects.filter(
                            minion_id__icontains=search_content).order_by(
                            'create_time')
                        data_list = getPage(request, app_data, 15)
                    elif search_field == 'search_svn_url':
                        app_data = AppRelease.objects.filter(
                            app_svn_url__icontains=search_content).order_by(
                            'create_time')
                        data_list = getPage(request, app_data, 15)
                    else:
                        data_list = ""
                return render(request, 'release_sys/app_release.html',
                              {'data_list': data_list, 'search_field': search_field,
                           'search_content': search_content})
            else:
                username = request.user.username
                try:
                    app_auth_app_data = AppAuth.objects.get(username=username).app_perms.split(',')
                except Exception as e:
                    app_auth_app_data = ''
                if search_content is '':
                    app_data = AppRelease.objects.filter(app_name__in=app_auth_app_data).order_by('create_time')
                    data_list = getPage(request, app_data, 15)
                else:
                    if search_field == 'search_app_name':
                        app_data = AppRelease.objects.filter(app_name__in=app_auth_app_data).filter(
                            app_name__icontains=search_content).order_by(
                            'create_time')
                        data_list = getPage(request, app_data, 15)
                    elif search_field == 'search_minion_id':
                        app_data = AppRelease.objects.filter(app_name__in=app_auth_app_data).filter(
                            minion_id__icontains=search_content).order_by(
                            'create_time')
                        data_list = getPage(request, app_data, 15)
                    else:
                        data_list = ""
                return render(request, 'release_sys/app_release.html',
                              {'data_list': data_list, 'search_field': search_field,
                           'search_content': search_content})

    except Exception as e:
        logger.error('应用发布页面有问题:'+str(e))
        return render(request, 'release_sys/app_release.html')


# 发布系统 应用发布页ajax提交处理
def app_release_ajax(request):
    result = {'result': None, 'status': False}
    app_log = []
    try:
        if request.is_ajax():
            # 在ajax提交时候多一个字段作为标识，来区分多个ajax提交哈，厉害！
            if request.GET.get('app_tag_key') == 'modal_search_minion_id':
                minion_id = request.GET.get('minion_id')
                sys = request.GET.get('sys_type')
                minion_id_list = MinionList.objects.filter(minion_id__icontains=minion_id, sys=sys).order_by(
                    'create_date').values_list('minion_id', flat=True)
                result['result'] = list(minion_id_list)
                result['status'] = True
                # 返回字典之外的需要把参数safe改成false如：JsonResponse([1, 2, 3], safe=False)
                return JsonResponse(result)
            elif request.POST.get('app_tag_key') == 'app_add' and request.user.is_superuser:
                obj = AppReleaseAddForm(request.POST)
                if obj.is_valid():
                    # 由于git更新方式是后期添加的，为了不添加多余目录，和svn检出目录共用一个目录
                    app_svn_co_path = settings.SITE_BASE_SVN_PATH + time.strftime('%Y%m%d_%H%M%S')
                    AppRelease.objects.create(app_name=obj.cleaned_data["app_name"],
                                              sys_type=obj.cleaned_data["sys_type"],
                                              minion_id=obj.cleaned_data["minion_id"],
                                              app_path=obj.cleaned_data["app_path"],
                                              app_path_owner=obj.cleaned_data["app_path_owner"],
                                              app_svn_url=obj.cleaned_data["app_svn_url"],
                                              app_svn_user=obj.cleaned_data["app_svn_user"],
                                              app_svn_password=obj.cleaned_data["app_svn_password"],
                                              app_git_url=obj.cleaned_data["app_git_url"],
                                              app_git_user=obj.cleaned_data["app_git_user"],
                                              app_git_password=obj.cleaned_data["app_git_password"],
                                              app_git_branch=obj.cleaned_data["app_git_branch"],
                                              app_svn_co_path=app_svn_co_path,
                                              execution_style=obj.cleaned_data["execution_style"],
                                              operation_content=obj.cleaned_data["operation_content"],
                                              operation_arguments=obj.cleaned_data["operation_arguments"],
                                              app_backup_path=obj.cleaned_data["app_backup_path"],
                                              description=obj.cleaned_data["description"])
                    result['result'] = '成功'
                    result['status'] = True
                else:
                    error_str = obj.errors.as_json()
                    result['result'] = json.loads(error_str)
                return JsonResponse(result)
            elif request.POST.get('app_tag_key') == 'app_update' and request.user.is_superuser:
                obj = AppReleaseUpdateForm(request.POST)
                if obj.is_valid():
                    app_svn_co_path = AppRelease.objects.get(
                        app_name=obj.cleaned_data["app_name"]).app_svn_co_path
                    # 只要svn或者git的url/branch有变化就删除检出目录
                    source_app_svn_url = AppRelease.objects.get(
                        app_name=obj.cleaned_data["app_name"]).app_svn_url
                    update_app_svn_url = obj.cleaned_data["app_svn_url"]
                    source_app_git_url = AppRelease.objects.get(
                        app_name=obj.cleaned_data["app_name"]).app_git_url
                    update_app_git_url = obj.cleaned_data["app_git_url"]
                    source_app_git_branch = AppRelease.objects.get(
                        app_name=obj.cleaned_data["app_name"]).app_git_branch
                    update_app_git_branch = obj.cleaned_data["app_git_branch"]
                    # 判断下svn/git地址有没改变，如果有改变删除master上的svn目录并重置svn两版本字段为none，下次有更新再重新检出，但注意目录路径是不改变的！！
                    # 主要是因为发现如果svn目录不重新生成会出现旧的svn文件不会在新svn地址检出后清除掉
                    if source_app_svn_url == update_app_svn_url and source_app_git_url == update_app_git_url and source_app_git_branch == update_app_git_branch:
                        AppRelease.objects.filter(app_name=obj.cleaned_data["app_name"]).update(
                            sys_type=obj.cleaned_data["sys_type"],
                            minion_id=obj.cleaned_data["minion_id"],
                            app_path=obj.cleaned_data["app_path"],
                            app_path_owner=obj.cleaned_data["app_path_owner"],
                            app_svn_url=obj.cleaned_data["app_svn_url"],
                            app_svn_user=obj.cleaned_data["app_svn_user"],
                            app_svn_password=obj.cleaned_data["app_svn_password"],
                            app_git_url=obj.cleaned_data["app_git_url"],
                            app_git_user=obj.cleaned_data["app_git_user"],
                            app_git_password=obj.cleaned_data["app_git_password"],
                            app_git_branch=obj.cleaned_data["app_git_branch"],
                            execution_style=obj.cleaned_data["execution_style"],
                            operation_content=obj.cleaned_data["operation_content"],
                            operation_arguments=obj.cleaned_data["operation_arguments"],
                            app_backup_path=obj.cleaned_data["app_backup_path"],
                            description=obj.cleaned_data["description"])
                        result['result'] = '成功'
                        result['status'] = True
                    else:
                        with requests.Session() as s:
                            saltapi = SaltAPI(session=s)
                            if saltapi.get_token() is False:
                                error_data = '更新应用删除应用旧检出目录获取SaltAPI调用get_token请求出错'
                                logger.error(error_data)
                                result['result'] = error_data
                                return JsonResponse(result)
                            else:
                                response_data = saltapi.file_directory_exists_api(tgt=settings.SITE_SALT_MASTER,
                                                                                  arg=[app_svn_co_path])
                                # 当调用api失败的时候会返回false
                                if response_data is False:
                                    error_data = '更新应用删除应用旧检出目录失败，SaltAPI调用file_directory_exists_api请求出错'
                                    logger.error(error_data)
                                    result['result'] = error_data
                                    return JsonResponse(result)
                                else:
                                    response_data = response_data['return'][0][settings.SITE_SALT_MASTER]
                                    # 判断一下svn检出的目录是否存在，因为如果没发布过，目录还没生成，存在的话删，
                                    # 不然新svn检出和旧svn检出内容会重叠导致后面同步文件不对
                                    if response_data is True:
                                        response_data = saltapi.file_remove_api(tgt=settings.SITE_SALT_MASTER,
                                                                                arg=[app_svn_co_path])
                                        # 当调用api失败的时候会返回false
                                        if response_data is False:
                                            error_data = '删除应用旧检出目录失败，SaltAPI调用file_remove_api请求出错'
                                            logger.error(error_data)
                                            result['result'] = error_data
                                            return JsonResponse(result)
                                        else:
                                            response_data = response_data['return'][0][settings.SITE_SALT_MASTER]
                                            if response_data is True:
                                                # 删除成功后提交更新，记得把应用svn版本和成功svn版本还原None,可以不更新检出目录
                                                # 检出目录还是不变，在做发布的时候会重新自动创建出来不用担心
                                                AppRelease.objects.filter(app_name=obj.cleaned_data["app_name"]).update(
                                                    sys_type=obj.cleaned_data["sys_type"],
                                                    minion_id=obj.cleaned_data["minion_id"],
                                                    app_path=obj.cleaned_data["app_path"],
                                                    app_path_owner=obj.cleaned_data["app_path_owner"],
                                                    app_svn_url=obj.cleaned_data["app_svn_url"],
                                                    app_svn_user=obj.cleaned_data["app_svn_user"],
                                                    app_svn_password=obj.cleaned_data["app_svn_password"],
                                                    app_git_url=obj.cleaned_data["app_git_url"],
                                                    app_git_user=obj.cleaned_data["app_git_user"],
                                                    app_git_password=obj.cleaned_data["app_git_password"],
                                                    app_git_branch=obj.cleaned_data["app_git_branch"],
                                                    execution_style=obj.cleaned_data["execution_style"],
                                                    operation_content=obj.cleaned_data["operation_content"],
                                                    operation_arguments=obj.cleaned_data["operation_arguments"],
                                                    app_backup_path=obj.cleaned_data["app_backup_path"],
                                                    description=obj.cleaned_data["description"],
                                                    app_svn_version=None, app_svn_version_success=None,
                                                    app_git_co_status=None)
                                                result['result'] = '成功'
                                                result['status'] = True
                                            else:
                                                logger.error('更新应用删除应用检出目录结果错误：' + str(response_data))
                                                result['result'] = '更新应用删除应用检出目录结果错误：' + str(response_data)
                                                return JsonResponse(result)
                                    else:
                                        AppRelease.objects.filter(app_name=obj.cleaned_data["app_name"]).update(
                                            sys_type=obj.cleaned_data["sys_type"],
                                            minion_id=obj.cleaned_data["minion_id"],
                                            app_path=obj.cleaned_data["app_path"],
                                            app_path_owner=obj.cleaned_data["app_path_owner"],
                                            app_svn_url=obj.cleaned_data["app_svn_url"],
                                            app_svn_user=obj.cleaned_data["app_svn_user"],
                                            app_svn_password=obj.cleaned_data["app_svn_password"],
                                            app_git_url=obj.cleaned_data["app_git_url"],
                                            app_git_user=obj.cleaned_data["app_git_user"],
                                            app_git_password=obj.cleaned_data["app_git_password"],
                                            app_git_branch=obj.cleaned_data["app_git_branch"],
                                            execution_style=obj.cleaned_data["execution_style"],
                                            operation_content=obj.cleaned_data["operation_content"],
                                            operation_arguments=obj.cleaned_data["operation_arguments"],
                                            app_backup_path=obj.cleaned_data["app_backup_path"],
                                            description=obj.cleaned_data["description"])
                                        result['result'] = '成功'
                                        result['status'] = True

                else:
                    error_str = obj.errors.as_json()
                    result['result'] = json.loads(error_str)
                return JsonResponse(result)
            elif request.POST.get('app_tag_key') == 'app_delete' and request.user.is_superuser:
                app_name = request.POST.get('app_name')
                delete_app_file_select = request.POST.get('delete_app_file_select')
                try:
                    app_svn_co_path = AppRelease.objects.get(app_name=app_name).app_svn_co_path
                    app_path = AppRelease.objects.get(app_name=app_name).app_path
                    app_backup_path = AppRelease.objects.get(app_name=app_name).app_backup_path
                    minion_id = AppRelease.objects.get(app_name=app_name).minion_id
                    minion_id_list = minion_id.split(',')

                    app_group_exist = AppGroup.objects.filter(
                        app_group_members__regex=r'^%s$|^%s,|,%s$|,%s,' % (app_name, app_name, app_name, app_name)).exists()
                    if app_group_exist:
                        result['result'] = '该应用属于应用发布组的成员，请先从应用发布组中踢除该应用，再执行删除操作'
                        return JsonResponse(result)

                    with requests.Session() as s:
                        saltapi = SaltAPI(session=s)
                        if saltapi.get_token() is False:
                            error_data = '删除应用获取SaltAPI调用get_token请求出错'
                            logger.error(error_data)
                            result['result'] = error_data
                            return JsonResponse(result)
                        else:
                            # 判断一下svn检出的目录是否存在，因为如果没发布过，目录还没生成，存在的话删除项目的时候要顺带删除
                            response_data = saltapi.file_directory_exists_api(tgt=settings.SITE_SALT_MASTER,
                                                                              arg=[app_svn_co_path])
                            # 当调用api失败的时候会返回false
                            if response_data is False:
                                error_data = '删除应用失败，SaltAPI调用file_directory_exists_api请求出错'
                                logger.error(error_data)
                                result['result'] = error_data
                                return JsonResponse(result)
                            else:
                                response_data = response_data['return'][0][settings.SITE_SALT_MASTER]
                                if response_data is True:
                                    # 删除master端项目的检出目录
                                    response_data = saltapi.file_remove_api(tgt=settings.SITE_SALT_MASTER,
                                                                            arg=[app_svn_co_path])
                                    # 当调用api失败的时候会返回false
                                    if response_data is False:
                                        error_data = '删除应用失败，SaltAPI调用file_remove_api请求出错'
                                        logger.error(error_data)
                                        result['result'] = error_data
                                        return JsonResponse(result)
                                    else:
                                        response_data = response_data['return'][0][settings.SITE_SALT_MASTER]
                                        if response_data is True:
                                            pass
                                        else:
                                            logger.error('删除应用结果错误：' + str(response_data))
                                            result['result'] = '删除应用结果错误：' + str(response_data)
                                            return JsonResponse(result)
                            if delete_app_file_select == 'delete_app_file':
                                for minion in minion_id_list:
                                    # 删除应用目录
                                    response_data = saltapi.file_directory_exists_api(tgt=minion, arg=[app_path])
                                    # 当调用api失败的时候会返回false
                                    if response_data is False:
                                        error_data = '删除应用时删除应用目录失败，SaltAPI调用file_directory_exists_api请求出错'
                                        logger.error(error_data)
                                        result['result'] = error_data
                                        return JsonResponse(result)
                                    else:
                                        response_data = response_data['return'][0][minion]
                                        # 判断一下svn检出的目录是否存在，因为如果没发布过，目录还没生成，存在的话删除项目的时候要顺带删除
                                        if response_data is True:
                                            response_data = saltapi.file_remove_api(tgt=minion, arg=[app_path])
                                            # 当调用api失败的时候会返回false
                                            if response_data is False:
                                                error_data = '删除应用时删除应用目录失败，SaltAPI调用file_remove_api请求出错'
                                                logger.error(error_data)
                                                result['result'] = error_data
                                                return JsonResponse(result)
                                            else:
                                                response_data = response_data['return'][0][minion]
                                                if response_data is True:
                                                    pass
                                                else:
                                                    logger.error('删除应用时删除应用目录结果错误：' + str(response_data))
                                                    result['result'] = '删除应用时删除应用目录结果错误：' + str(response_data)
                                                    return JsonResponse(result)
                                    # 删除备份目录
                                    response_data = saltapi.file_directory_exists_api(tgt=minion, arg=[app_backup_path])
                                    # 当调用api失败的时候会返回false
                                    if response_data is False:
                                        error_data = '删除应用时删除应用备份目录失败，SaltAPI调用file_directory_exists_api请求出错'
                                        logger.error(error_data)
                                        result['result'] = error_data
                                        return JsonResponse(result)
                                    else:
                                        response_data = response_data['return'][0][minion]
                                        # 判断一下svn检出的目录是否存在，因为如果没发布过，目录还没生成，存在的话删除项目的时候要顺带删除
                                        if response_data is True:
                                            response_data = saltapi.file_remove_api(tgt=minion, arg=[app_backup_path])
                                            # 当调用api失败的时候会返回false
                                            if response_data is False:
                                                error_data = '删除应用时删除应用备份目录失败，SaltAPI调用file_remove_api请求出错'
                                                logger.error(error_data)
                                                result['result'] = error_data
                                                return JsonResponse(result)
                                            else:
                                                response_data = response_data['return'][0][minion]
                                                if response_data is True:
                                                    pass
                                                else:
                                                    logger.error('删除应用时删除应用备份目录结果错误：' + str(response_data))
                                                    result['result'] = '删除应用时删除应用备份目录结果错误：' + str(response_data)
                                                    return JsonResponse(result)
                            AppRelease.objects.get(app_name=app_name).delete()
                    result['result'] = '成功'
                    result['status'] = True
                except Exception as e:
                    result['result'] = str(e)
                return JsonResponse(result)
            elif request.GET.get('app_tag_key') == 'check_svn':
                app_name = request.GET.get("app_name")
                try:
                    app_data = AppRelease.objects.get(app_name=app_name)
                    with requests.Session() as s:
                        saltapi = SaltAPI(session=s)
                        if saltapi.get_token() is False:
                            error_data = '应用发布查询svn版本获取SaltAPI调用get_token请求出错'
                            result['result'] = error_data
                            return JsonResponse(result)
                        else:
                            response_data = saltapi.cmd_run_api(tgt=settings.SITE_SALT_MASTER, arg=[
                                'svn info %s  --username=%s --password=%s --no-auth-cache' % (
                                    app_data.app_svn_url, app_data.app_svn_user,
                                    app_data.app_svn_password), 'reset_system_locale=false'])
                            # 当调用api失败的时候会返回false
                            if response_data is False:
                                error_data = '应用发布查询svn版本失败，SaltAPI调用async_cmd_run_api请求出错'
                                result['result'] = error_data
                                return JsonResponse(result)
                            else:
                                response_data = response_data['return'][0][settings.SITE_SALT_MASTER]
                                try:
                                    svn_version = re.search(r'Revision: (\d+)', response_data).group(1)
                                    result['result'] = svn_version
                                    result['status'] = True
                                    return JsonResponse(result)
                                except Exception as e:
                                    logger.error('检查svn版本结果错误：' + str(e) + str(response_data))
                                    result['result'] = '检查svn版本结果错误：' + str(response_data)
                                    return JsonResponse(result)
                except Exception as e:
                    logger.error('检查svn版本出错：'+str(e))
                    result['result'] = '检查出错'
                    return JsonResponse(result)
            elif request.GET.get('app_tag_key') == 'search_app_log':
                try:
                    app_name = request.GET.get("app_name")
                    log_data = AppReleaseLog.objects.filter(app_name=app_name).order_by(
                        '-create_time')
                    data_list = getPage(request, log_data, 1)
                    log_content = ''
                    create_time = ''
                    release_result = ''
                    log_app_username = ''
                    for data in data_list:
                        log_content = eval(data.log_content)
                        create_time = data.create_time.strftime('%Y-%m-%d %X')
                        release_result = data.release_result
                        log_app_username = data.username
                    if data_list.has_previous():
                        previous_page_number = data_list.previous_page_number()
                    else:
                        previous_page_number = 0
                    if data_list.has_next():
                        next_page_number = data_list.next_page_number()
                    else:
                        next_page_number = 0
                    result = {'status': True, 'log_app_username': log_app_username, 'create_time': create_time, 'release_result': release_result, 'has_previous': data_list.has_previous(), 'previous_page_number': previous_page_number, 'number': data_list.number, 'num_pages': data_list.paginator.num_pages, 'has_next': data_list.has_next(), 'next_page_number': next_page_number, 'log_content': log_content}
                    return JsonResponse(result)
                except Exception as e:
                    logger.error('查询日志错误了'+str(e))
                    return JsonResponse(result)
            elif request.POST.get('app_tag_key') == 'release_app':
                app_name = request.POST.get('app_name')
                release_svn_version = request.POST.get('release_svn_version', 'HEAD')
                app_data = AppRelease.objects.get(app_name=app_name)
                # 判断执行的是否为单项操作执行判断，如果不是就是执行操作步骤顺序的操作
                single_cmd = request.POST.get('single_cmd')
                if single_cmd:
                    operation_content = [single_cmd]
                else:
                    operation_content = app_data.operation_content.split(',')
                operation_arguments = app_data.operation_arguments
                operation_arguments = eval(operation_arguments)
                app_svn_co_path = app_data.app_svn_co_path
                app_svn_url = app_data.app_svn_url
                app_svn_user = app_data.app_svn_user
                app_svn_password = app_data.app_svn_password
                app_svn_version_success = app_data.app_svn_version_success
                app_git_url = app_data.app_git_url
                app_git_user = app_data.app_git_user
                app_git_password = app_data.app_git_password
                app_git_branch = app_data.app_git_branch
                app_git_co_status = app_data.app_git_co_status
                app_path = app_data.app_path
                sys_type = app_data.sys_type
                app_path_owner = app_data.app_path_owner
                try:
                    # 由于用的salt来做发布所以如果minion离线或不存在删除了就无法执行，所以要判断，另外还有一个原因是minion管理表如果
                    # 删除了某个minion会触发try的except
                    try:
                        minion_id_list = app_data.minion_id.split(',')
                        for minion_id in minion_id_list:
                            minion_status = MinionList.objects.get(minion_id=minion_id).minion_status
                            if minion_status == '离线':
                                app_log.append('\n应用minion_id:%s离线了，请确认全部在线或移除离线minino_id才可执行应用发布' % minion_id)
                                result['result'] = app_log
                                return JsonResponse(result)
                    except Exception as e:
                        logger.error('\n检查应用的Minion_ID出错，可能有Minion已经不存在了，报错信息:'+str(e))
                        app_log.append('\n检查应用的Minion_ID出错，可能有Minion已经不存在了，报错信息:'+str(e))
                        result['result'] = app_log
                        return JsonResponse(result)
                    for minion_id in minion_id_list:
                        # svn版本需要在这里获取，因为下面需要用到版本判断是检出还是更新操作，
                        # 如果在上面就定义好，那么多个minion_id的新项目第一个id是检出后也全是检出，因为判断版本的时候都是空
                        app_svn_version = AppRelease.objects.get(app_name=app_name).app_svn_version
                        app_log.append(('-'*10+('Minion_ID:%s开始发布 时间戳%s' % (minion_id, time.strftime('%X')))+'-'*10).center(88)+'\n')
                        for operation in operation_content:
                            if operation == 'SVN更新':
                                app_log.append('\n\n开始执行SVN更新-> 时间戳%s\n' % time.strftime('%X'))
                                with requests.Session() as s:
                                    saltapi = SaltAPI(session=s)
                                    if saltapi.get_token() is False:
                                        app_log.append('\n更新svn后台出错_error(0)，请联系管理员. 时间戳%s\n' % time.strftime('%X'))
                                        result['result'] = app_log
                                        return JsonResponse(result)
                                    else:
                                        # 判断是否有应用svn版本号，如果有说明已经检出过，那就使用更新up，如果没有就用检出co
                                        if app_svn_version:
                                            cmd_data = 'svn up -r %s %s --no-auth-cache --non-interactive  --username=%s --password=%s' % (
                                                release_svn_version, app_svn_co_path, app_svn_user, app_svn_password)
                                            # 用来做执行结果判断的，因为结果有很多意外情况，下面是对的情况下会出现的关键字
                                            check_data = "Updating '%s'" % app_svn_co_path
                                        else:
                                            cmd_data = 'svn co -r %s %s  %s --username=%s --password=%s --non-interactive --no-auth-cache' % (
                                                release_svn_version, app_svn_url, app_svn_co_path, app_svn_user, app_svn_password)
                                            check_data = 'Checked out revision'
                                        response_data = saltapi.cmd_run_api(tgt=settings.SITE_SALT_MASTER, arg=[
                                            cmd_data, 'reset_system_locale=false',"shell='/bin/bash'","runas='root'"])
                                        # 当调用api失败的时候会返回false
                                        if response_data is False:
                                            app_log.append('\n更新svn后台出错_error(1)，请联系管理员. 时间戳%s\n' % time.strftime('%X'))
                                            result['result'] = app_log
                                            return JsonResponse(result)
                                        else:
                                            response_data = response_data['return'][0][settings.SITE_SALT_MASTER]

                                            if check_data in response_data:
                                                # 用正则获取版本号，并更新一下数据表,这里发现有出错的可能就是正则没匹配到，所以再加一层try
                                                try:
                                                    app_svn_version = re.search(r'revision (\d+)\.', response_data).group(1)
                                                    AppRelease.objects.filter(app_name=app_name).update(
                                                        app_svn_version=app_svn_version)
                                                    app_svn_version_success = app_svn_version
                                                    app_log.append('\n'+str(response_data)+'\n\nSVN更新完成<- 时间戳%s\n' % time.strftime('%X'))
                                                except Exception as e:
                                                    app_log.append('\nSVN更新失败:\n'+str(response_data)+'\n时间戳%s' % time.strftime('%X'))
                                                    result['result'] = app_log
                                                    return JsonResponse(result)
                                            else:
                                                app_log.append('\nSVN更新失败:'+str(response_data)+'\n时间戳%s' % time.strftime('%X'))
                                                result['result'] = app_log
                                                return JsonResponse(result)
                            if operation == 'GIT更新':
                                # 目前只支持http方式的git，下面是拼接把用户名密码拼接进去这样就不用输入了,如果用户名有@需要转义
                                app_git_user_new = app_git_user.replace('@', '%40')
                                app_git_url_join_usr_passwd = app_git_url.split('://')[
                                                                  0] + '://' + app_git_user_new + ':' + app_git_password + '@' + \
                                                              app_git_url.split('://')[1]
                                app_log.append('\n\n开始执行GIT更新-> 时间戳%s\n' % time.strftime('%X'))
                                with requests.Session() as s:
                                    saltapi = SaltAPI(session=s)
                                    if saltapi.get_token() is False:
                                        app_log.append('\n更新git后台出错_error(0)，请联系管理员. 时间戳%s\n' % time.strftime('%X'))
                                        result['result'] = app_log
                                        return JsonResponse(result)
                                    else:
                                        # 判断状态是否为True，如果有说明已经检出过，那就使用更新pull，如果没有就用git clone
                                        if app_git_co_status is not True:
                                            app_log.append('\n\ngit clone ....\n')
                                            response_data = saltapi.git_clone_api(tgt=settings.SITE_SALT_MASTER, arg=[
                                                'cwd=%s' % app_svn_co_path.rsplit('/', 1)[0],
                                                'url=%s' % app_git_url_join_usr_passwd,
                                                'name=%s' % app_svn_co_path.rsplit('/', 1)[1],
                                                'opts="-b %s"' % app_git_branch])
                                            check_data = True
                                        else:
                                            if release_svn_version == 'HEAD':
                                                response_data = saltapi.git_pull_api(tgt=settings.SITE_SALT_MASTER,
                                                                                     arg=[app_svn_co_path])
                                                check_data = 'Updating'
                                            else:
                                                response_data = saltapi.git_reset_api(tgt=settings.SITE_SALT_MASTER,
                                                                                      arg=[app_svn_co_path,
                                                                                           'opts="--hard %s"' % release_svn_version])
                                                check_data = 'HEAD is now at'
                                        # 当调用api失败的时候会返回false
                                        if response_data is False:
                                            app_log.append('\n更新svn后台出错_error(1)，请联系管理员. 时间戳%s\n' % time.strftime('%X'))
                                            result['result'] = app_log
                                            return JsonResponse(result)
                                        else:
                                            response_data = response_data['return'][0][settings.SITE_SALT_MASTER]
                                            # 对结果进行判断，妈的用salt的module方式还得自个判断结果，比较麻烦一点，而且if还有可能代码错误得加try
                                            try:
                                                if response_data is True or check_data in response_data or 'Already up' in response_data:
                                                    try:
                                                        AppRelease.objects.filter(app_name=app_name).update(
                                                            app_git_co_status=True)
                                                        app_log.append('\n'+str(response_data)+'\n\nGIT更新完成<- 时间戳%s\n' % time.strftime('%X'))
                                                    except Exception as e:
                                                        app_log.append('\nGIT更新失败:\n'+str(response_data)+'\n时间戳%s' % time.strftime('%X'))
                                                        result['result'] = app_log
                                                        return JsonResponse(result)
                                                else:
                                                    app_log.append('\nGIT更新失败:'+str(response_data)+'\n时间戳%s' % time.strftime('%X'))
                                                    result['result'] = app_log
                                                    return JsonResponse(result)
                                            except Exception as e:
                                                app_log.append(
                                                    '\nGIT更新失败:' + str(response_data) + '\n时间戳%s' % time.strftime('%X'))
                                                result['result'] = app_log
                                                return JsonResponse(result)
                            elif operation == '同步文件':
                                sync_file_method = operation_arguments.get('文件同步方法', 'salt')
                                if sync_file_method == 'salt':
                                    source_path = app_svn_co_path.rstrip('/').rsplit('/', 1)[1]
                                    sync_file_style = operation_arguments['文件同步方式']
                                    svn_symlink_path = settings.SITE_BASE_SVN_SYMLINK_PATH + source_path
                                    app_log.append('\n\n开始执行同步文件-> 时间戳%s\n' % time.strftime('%X'))
                                    with requests.Session() as s:
                                        saltapi = SaltAPI(session=s)
                                        if saltapi.get_token() is False:
                                            app_log.append('\n同步文件后台出错_error(0)，请联系管理员.  时间戳%s\n' % time.strftime('%X'))
                                            result['result'] = app_log
                                            return JsonResponse(result)
                                        else:
                                            # 先创建软连接
                                            response_data = saltapi.file_symlink_api(tgt=settings.SITE_SALT_MASTER,
                                                                                     arg=[app_svn_co_path, svn_symlink_path])
                                            if response_data is False:
                                                app_log.append('\n同步文件后台出错_error(1)，请联系管理员. 时间戳%s\n' % time.strftime('%X'))
                                                result['result'] = app_log
                                                return JsonResponse(result)
                                            else:
                                                if response_data['return'][0][settings.SITE_SALT_MASTER] is not True:
                                                    # 如果软连接创建失败会返回：{'return': [{'192.168.100.170': False}]}
                                                    app_log.append('同步文件过程中，创建软连接失败\n' + str(response_data))
                                                    app_log.append('\n' + '文件同步失败！！ 时间戳%s\n' % time.strftime('%X'))
                                                    result['result'] = app_log
                                                    return JsonResponse(result)
                                            # 执行文件同步
                                            jid = saltapi.async_state_api(tgt=minion_id, arg=["rsync_dir", "pillar={'sync_file_method':'%s','source_path':'%s','name_path':'%s','user':'%s','sync_file_style':'%s'}" % (sync_file_method, source_path, app_path, app_path_owner, sync_file_style), "queue=True"])
                                            if jid is False:
                                                app_log.append('\n同步文件后台出错,SaltAPI调用async_state_api请求出错，请联系管理员. 时间戳%s\n' % time.strftime('%X'))
                                                result['result'] = app_log
                                                return JsonResponse(result)
                                            else:
                                                try:
                                                    jid = jid['return'][0]['jid']
                                                    check_count = 400
                                                    re_count = 0
                                                    time.sleep(10)
                                                    while check_count:
                                                        job_status = saltapi.job_active_api(tgt=minion_id, arg=jid)
                                                        if job_status is False:
                                                            app_log.append(
                                                                '\n同步文件后台出错,SaltAPI调用job_active_api请求出错，请联系管理员. 时间戳%s\n' % time.strftime('%X'))
                                                            result['result'] = app_log
                                                            return JsonResponse(result)
                                                        else:
                                                            value = job_status['return'][0][minion_id]
                                                            if value:
                                                                # 为真说明job还在执行，刚好用来恢复断线false的计数器
                                                                if re_count > 0:
                                                                    re_count = 0
                                                            # 这个留在这里做个说明，我发现在调用job_active_api接口的时候经常失败返回false了，感觉是接口有问题
                                                            # 而如果出现都是false用jid_api接口取到的结果就会是[{}]所以下面对这个要做一层判断，以免因为接口不稳导致没取到结果
                                                            # 另外注意这里value is False看上去好像和上面是if value是相反的可以直接用else代替，但是不行！因为当执行完毕返回是{}而{}和False是不同的！
                                                            elif value is False:
                                                                # 连续监测2次都是那就不用跑了直接返回离线结束呵呵
                                                                if re_count == 2:
                                                                    app_log.append('\n同步文件后台出错,您要发布的主机%s离线了，请联系管理员. 时间戳%s\n' % (minion_id, time.strftime('%X')))
                                                                    result['result'] = app_log
                                                                    return JsonResponse(result)
                                                                # re计数器不到3次则+1，继续下一轮循环
                                                                else:
                                                                    re_count += 1
                                                            # 当value等于[{}]时候说明job执行完毕了，则执行下面
                                                            else:
                                                                jid_data = saltapi.jid_api(jid=jid)
                                                                # 注意[{}] ！= False所以不能用if jid_data['return']判断是否有数据，这个坑埋了好久奶奶的！！！
                                                                if jid_data is False:
                                                                    app_log.append('\n同步文件后台出错,SaltAPI调用jid_api请求出错,jid:%s，请联系管理员. 时间戳%s\n' % (jid, time.strftime('%X')))
                                                                    result['result'] = app_log
                                                                    return JsonResponse(result)
                                                                elif jid_data['return'] == [{}]:
                                                                    # 这个判断没必要，只是留这里做个说明，我之前上面没有做if value is False判断的时候，如果job_active_api
                                                                    # 的结果全部false了也会正常跳出for循环，然后在这里会出现jid_data['return'] == [{}]的情况，因为false
                                                                    # 说明minion断线了，结果肯定取到空了；还有另一种情况就是还没有返回值的时候也会等于[{}],
                                                                    # 不过后面我在上面加了对false做判断这里就没必要了呵呵
                                                                    pass
                                                                else:
                                                                    format_result = format_state(jid_data)
                                                                    if type(format_result) == str:
                                                                        # 如果minion客户端停了会返回：{'return': [{'192.168.100.170': False}]}
                                                                        app_log.append(format_result)
                                                                        app_log.append(
                                                                            '\n' + '文件同步失败！！ 时间戳%s\n' % time.strftime('%X'))
                                                                        result['result'] = app_log
                                                                        return JsonResponse(result)
                                                                    else:
                                                                        try:
                                                                            failed_result = re.search(r'Failed:     (\d+)',
                                                                                                      format_result[0]).group(1)
                                                                            if int(failed_result) != 0:
                                                                                app_log.extend(format_result)
                                                                                app_log.append(
                                                                                    '\n' + '文件同步失败！！ 时间戳%s\n' % time.strftime(
                                                                                        '%X'))
                                                                                result['result'] = app_log
                                                                                return JsonResponse(result)
                                                                            else:
                                                                                app_log.extend(format_result)
                                                                                app_log.append(
                                                                                    '\n\n文件同步完成<- 时间戳%s\n' % time.strftime(
                                                                                        '%X'))
                                                                                break
                                                                        except Exception as e:
                                                                            app_log.append('\n' + '文件同步代码出错：' + str(
                                                                                e) + '\n时间戳%s' % time.strftime('%X'))
                                                                            result['result'] = app_log
                                                                            return JsonResponse(result)
                                                            check_count -= 1
                                                            time.sleep(15)
                                                    else:
                                                        app_log.append('\n' + '文件同步超过100分钟还没有结束，系统默认同步失败，如需获取同步结果请联系管理员通过jid：%s查看！！ 时间戳%s\n' % (jid, time.strftime('%X')))
                                                        result['result'] = app_log
                                                        return JsonResponse(result)
                                                except Exception as e:
                                                    app_log.append(str(e))
                                                    app_log.append('\n' + '文件同步失败！！ 时间戳%s\n' % time.strftime('%X'))
                                                    result['result'] = app_log
                                                    return JsonResponse(result)
                                                finally:
                                                    # 释放掉软连接
                                                    response_data = saltapi.file_remove_api(tgt=settings.SITE_SALT_MASTER,
                                                                                            arg=[svn_symlink_path])
                                                    # 当调用api失败的时候会返回false
                                                    if response_data is False:
                                                        app_log.append('删除软连接失败(0)，未避免目录不断膨胀请联系管理员删除软连接\n')
                                                    else:
                                                        response_data = response_data['return'][0][
                                                            settings.SITE_SALT_MASTER]
                                                        if response_data is True:
                                                            app_log.append('\n释放软连接成功\n')
                                                        else:
                                                            app_log.append('\n释放软连接失败(1)，未避免目录不断膨胀请联系管理员删除软连接\n')
                                elif sync_file_method == 'rsync':
                                    source_path = app_svn_co_path.rstrip('/').rsplit('/', 1)[1]
                                    sync_file_style = operation_arguments.get('文件同步方式', 'check_file')
                                    rsync_ip = operation_arguments.get('rsync源IP', '192.168.18.18')
                                    # salt-2018.3.0以前rsync的参数中没有additional_opts，无法指定很多东西，2018版本就有了，留这里为了新版使用
                                    rsync_port = operation_arguments.get('rsync源端口', '873')
                                    app_log.append('\n\n开始执行同步文件-> 时间戳%s\n' % time.strftime('%X'))
                                    with requests.Session() as s:
                                        saltapi = SaltAPI(session=s)
                                        if saltapi.get_token() is False:
                                            app_log.append('\n同步文件后台出错_error(0)，请联系管理员.  时间戳%s\n' % time.strftime('%X'))
                                            result['result'] = app_log
                                            return JsonResponse(result)
                                        else:
                                            if sys_type == 'windows':
                                                # windows下的rsync语法中路径写法比较特殊，所以要做下修改来适应，name_path存传递给后端SLS的name字段
                                                name_path = '/cygdrive/' + app_path.replace(':\\', '/').replace('\\', '/')
                                            else:
                                                name_path = app_path
                                            jid = saltapi.async_state_api(tgt=minion_id, arg=["rsync_dir",
                                                                                              "pillar={'sync_file_method':'%s','mkdir_path':'%s','rsync_ip':'%s','rsync_port':'%s','source_path':'%s','name_path':'%s','user':%s,'sync_file_style':'%s'}" % (
                                                                                              sync_file_method,app_path,
                                                                                              rsync_ip, rsync_port, source_path,
                                                                                              name_path, app_path_owner,
                                                                                              sync_file_style),
                                                                                              "concurrent=True"])

                                            if jid is False:
                                                app_log.append(
                                                    '\n同步文件后台出错,SaltAPI调用async_rsync_rsync_api请求出错，请联系管理员. 时间戳%s\n' % time.strftime(
                                                        '%X'))
                                                result['result'] = app_log
                                                return JsonResponse(result)
                                            else:
                                                try:
                                                    jid = jid['return'][0]['jid']
                                                    check_count = 400
                                                    re_count = 0
                                                    time.sleep(10)
                                                    while check_count:
                                                        job_status = saltapi.job_active_api(tgt=minion_id, arg=jid)
                                                        if job_status is False:
                                                            app_log.append(
                                                                '\n同步文件后台出错,SaltAPI调用job_active_api请求出错，请联系管理员. 时间戳%s\n' % time.strftime(
                                                                    '%X'))
                                                            result['result'] = app_log
                                                            return JsonResponse(result)
                                                        else:
                                                            value = job_status['return'][0][minion_id]
                                                            if value:
                                                                # 为真说明job还在执行，刚好用来恢复断线false的计数器
                                                                if re_count > 0:
                                                                    re_count = 0
                                                            # 这个留在这里做个说明，我发现在调用job_active_api接口的时候经常失败返回false了，感觉是接口有问题
                                                            # 而如果出现都是false用jid_api接口取到的结果就会是[{}]所以下面对这个要做一层判断，以免因为接口不稳导致没取到结果
                                                            # 另外注意这里value is False看上去好像和上面是if value是相反的可以直接用else代替，但是不行！因为当执行完毕返回是{}而{}和False是不同的！
                                                            elif value is False:
                                                                # 连续监测2次都是那就不用跑了直接返回离线结束呵呵
                                                                if re_count == 2:
                                                                    app_log.append(
                                                                        '\n同步文件后台出错,您要发布的主机%s离线了，请联系管理员. 时间戳%s\n' % (
                                                                        minion_id, time.strftime('%X')))
                                                                    result['result'] = app_log
                                                                    return JsonResponse(result)
                                                                # re计数器不到3次则+1，继续下一轮循环
                                                                else:
                                                                    re_count += 1
                                                            # 当value等于[{}]时候说明job执行完毕了，则执行下面
                                                            else:
                                                                jid_data = saltapi.jid_api(jid=jid)
                                                                # 注意[{}] ！= False所以不能用if jid_data['return']判断是否有数据，这个坑埋了好久奶奶的！！！
                                                                if jid_data is False:
                                                                    app_log.append(
                                                                        '\n同步文件后台出错,SaltAPI调用jid_api请求出错，请联系管理员. 时间戳%s\n' % time.strftime(
                                                                            '%X'))
                                                                    result['result'] = app_log
                                                                    return JsonResponse(result)
                                                                elif jid_data['return'] == [{}]:
                                                                    # 这个判断没必要，只是留这里做个说明，我之前上面没有做if value is False判断的时候，如果job_active_api
                                                                    # 的结果全部false了也会正常跳出for循环，然后在这里会出现jid_data['return'] == [{}]的情况，因为false
                                                                    # 说明minion断线了，结果肯定取到空了；还有另一种情况就是还没有返回值的时候也会等于[{}],
                                                                    # 不过后面我在上面加了对false做判断这里就没必要了呵呵
                                                                    pass
                                                                else:
                                                                    format_result = format_state(jid_data)
                                                                    if type(format_result) == str:
                                                                        # 如果minion客户端停了会返回：{'return': [{'192.168.100.170': False}]}
                                                                        app_log.append(format_result)
                                                                        app_log.append(
                                                                            '\n' + '文件同步失败！！ 时间戳%s\n' % time.strftime(
                                                                                '%X'))
                                                                        result['result'] = app_log
                                                                        return JsonResponse(result)
                                                                    else:
                                                                        try:
                                                                            failed_result = re.search(
                                                                                r'Failed:     (\d+)',
                                                                                format_result[0]).group(1)
                                                                            if int(failed_result) != 0:
                                                                                app_log.extend(format_result)
                                                                                app_log.append(
                                                                                    '\n' + '文件同步失败！！ 时间戳%s\n' % time.strftime(
                                                                                        '%X'))
                                                                                result['result'] = app_log
                                                                                return JsonResponse(result)
                                                                            else:
                                                                                app_log.extend(format_result)
                                                                                app_log.append(
                                                                                    '\n\n文件同步完成<- 时间戳%s\n' % time.strftime(
                                                                                        '%X'))
                                                                                break
                                                                        except Exception as e:
                                                                            app_log.append('\n' + '文件同步代码出错：' + str(
                                                                                e) + '\n时间戳%s' % time.strftime('%X'))
                                                                            result['result'] = app_log
                                                                            return JsonResponse(result)
                                                            check_count -= 1
                                                            time.sleep(15)
                                                    else:
                                                        app_log.append(
                                                            '\n' + '文件同步超过100分钟还没有结束，系统默认同步失败，如需获取同步结果请联系管理员通过jid：%s查看！！ 时间戳%s\n' % (
                                                            jid, time.strftime('%X')))
                                                        result['result'] = app_log
                                                        return JsonResponse(result)
                                                except Exception as e:
                                                    app_log.append(str(e))
                                                    app_log.append('\n' + '文件同步失败！！ 时间戳%s\n' % time.strftime('%X'))
                                                    result['result'] = app_log
                                                    return JsonResponse(result)
                            elif operation == '应用停止':
                                app_log.append('\n\n开始执行应用服务停止操作->')
                                if '停止服务名' in operation_arguments:
                                    stop_server_name = operation_arguments['停止服务名']
                                    with requests.Session() as s:
                                        saltapi = SaltAPI(session=s)
                                        if saltapi.get_token() is False:
                                            app_log.append('\n应用停止后台出错_error(0)，请联系管理员')
                                            result['result'] = app_log
                                            return JsonResponse(result)
                                        else:
                                            response_data = saltapi.service_available_api(tgt=minion_id, arg=[stop_server_name])
                                            if response_data is False:
                                                app_log.append('\n应用停止后台出错_error(1)，请联系管理员')
                                                result['result'] = app_log
                                                return JsonResponse(result)
                                            else:
                                                if response_data['return'][0][minion_id] is False:
                                                    app_log.append('\n' + '应用停止失败,请确定是否存在该服务！！')
                                                    result['result'] = app_log
                                                    return JsonResponse(result)
                                                elif response_data['return'][0][minion_id] is True:
                                                    response_data = saltapi.service_stop_api(tgt=minion_id, arg=[stop_server_name])
                                                    # 当调用api失败的时候会返回false
                                                    if response_data is False:
                                                        app_log.append('\n应用停止后台出错_error(2)，请联系管理员')
                                                        result['result'] = app_log
                                                        return JsonResponse(result)
                                                    else:
                                                        stop_data = response_data['return'][0][minion_id]
                                                        response_data = saltapi.service_status_api(tgt=minion_id,
                                                                                                   arg=[stop_server_name])
                                                        # 当调用api失败的时候会返回false
                                                        if response_data is False:
                                                            app_log.append('\n应用停止后台出错_error(3)，请联系管理员')
                                                            result['result'] = app_log
                                                            return JsonResponse(result)
                                                        elif response_data['return'][0][minion_id] is False:
                                                            app_log.append('\n'+'应用停止成功<-\n')
                                                        elif response_data['return'][0][minion_id] is True:
                                                            app_log.append('\n'+'应用停止失败，程序还在运行中。')
                                                            result['result'] = app_log
                                                            return JsonResponse(result)
                                                        else:
                                                            app_log.append('\n'+'应用停止失败,执行结果：'+str(stop_data)+str(response_data['return'][0][minion_id]))
                                                            result['result'] = app_log
                                                            return JsonResponse(result)
                                                else:
                                                    app_log.append('\n' + '应用停止失败查询服务时没有返回正确结果,执行结果：' + str(
                                                        response_data['return'][0][minion_id]))
                                                    result['result'] = app_log
                                                    return JsonResponse(result)
                                elif '停止命令' in operation_arguments:
                                    stop_cmd = operation_arguments['停止命令']
                                    if sys_type == 'windows':
                                        stop_cmd = stop_cmd+'&& echo %errorlevel%'
                                        split_cmd = '\r\n'
                                    else:
                                        stop_cmd = stop_cmd + '; echo $?'
                                        split_cmd = '\n'
                                    with requests.Session() as s:
                                        saltapi = SaltAPI(session=s)
                                        if saltapi.get_token() is False:
                                            app_log.append('\n应用停止命令后台出错_error(4)，请联系管理员')
                                            result['result'] = app_log
                                            return JsonResponse(result)
                                        else:
                                            response_data = saltapi.cmd_run_api(tgt=minion_id, arg=[stop_cmd,"shell='/bin/bash'","runas='root'"])
                                            # 当调用api失败的时候会返回false
                                            if response_data is False:
                                                app_log.append('\n应用停止命令后台出错_error(5)，请联系管理员')
                                                result['result'] = app_log
                                                return JsonResponse(result)
                                            else:
                                                try:
                                                    response_data = response_data['return'][0][minion_id].rsplit(split_cmd, 1)
                                                    # 发现有的命令没有输出那么最终只会有成功失败的0、1返回这时候列表长度就=1
                                                    if len(response_data) == 1:
                                                        if response_data[0] == '0':
                                                            app_log.append('\n' + '应用停止成功<-\n')
                                                        else:
                                                            app_log.append('\n' + '应用停止失败:' + response_data[0])
                                                            result['result'] = app_log
                                                            return JsonResponse(result)
                                                    else:
                                                        if response_data[1] == '0':
                                                            app_log.append('\n' + '应用停止成功<-\n')
                                                        else:
                                                            app_log.append('\n' + '应用停止失败:' + response_data[0])
                                                            result['result'] = app_log
                                                            return JsonResponse(result)
                                                except Exception as e:
                                                    app_log.append('\n' + '应用停止失败_error(6):' + str(response_data))
                                                    result['result'] = app_log
                                                    return JsonResponse(result)
                                elif '任务计划停止' in operation_arguments:
                                    start_cmd = operation_arguments['任务计划停止']
                                    if sys_type == 'linux':
                                        logger.error('应用停止失败，应用停止中《任务计划启动》启动方式只适用于windows')
                                        app_log.append('\n\n应用停止失败，应用停止中《任务计划停止》停止方式只适用于windows')
                                        result['result'] = app_log
                                        return JsonResponse(result)
                                    with requests.Session() as s:
                                        saltapi = SaltAPI(session=s)
                                        if saltapi.get_token() is False:
                                            app_log.append('\n应用停止命令后台出错_error(1)，请联系管理员')
                                            result['result'] = app_log
                                            return JsonResponse(result)
                                        else:
                                            response_data = saltapi.task_stop_api(tgt=minion_id, arg=[start_cmd])
                                            # 当调用api失败的时候会返回false
                                            if response_data is False:
                                                app_log.append('\n应用停止命令后台出错_error(2)，请联系管理员')
                                                result['result'] = app_log
                                                return JsonResponse(result)
                                            else:
                                                try:
                                                    response_data = response_data['return'][0][minion_id]
                                                    if response_data is True:
                                                        app_log.append('\n' + '应用停止成功<-\n')
                                                    else:
                                                        app_log.append('\n'+'应用停止失败:'+response_data)
                                                        result['result'] = app_log
                                                        return JsonResponse(result)
                                                except Exception as e:
                                                    app_log.append('\n' + '应用停止后台出错_error(3):' + str(e))
                                                    result['result'] = app_log
                                                    return JsonResponse(result)
                                elif '映像名称和命令行' in operation_arguments:
                                    stop_cmd = operation_arguments['映像名称和命令行']
                                    data = stop_cmd.split('|')
                                    if len(data) != 2:
                                        logger.error('应用停止失败,填写的命令不符合规范')
                                        app_log.append('\n\n应用停止失败,填写的命令不符合规范')
                                        result['result'] = app_log
                                        return JsonResponse(result)
                                    exe_name = data[0].strip()
                                    cmdline = data[1].strip()
                                    with requests.Session() as s:
                                        saltapi = SaltAPI(session=s)
                                        if saltapi.get_token() is False:
                                            app_log.append('\n应用停止命令后台出错_error(7)，请联系管理员')
                                            result['result'] = app_log
                                            return JsonResponse(result)
                                        else:
                                            # 查看是否有映像名称的id存在，支持模糊搜索
                                            response_data = saltapi.ps_pgrep_api(tgt=minion_id, arg=[exe_name])
                                            # 当调用api失败的时候会返回false
                                            if response_data is False:
                                                app_log.append('\n应用停止命令后台出错_error(8)，请联系管理员')
                                                result['result'] = app_log
                                                return JsonResponse(result)
                                            else:
                                                try:
                                                    response_data = response_data['return'][0][minion_id]
                                                    if isinstance(response_data, list):
                                                        for pid in response_data:
                                                            response_data = saltapi.ps_proc_info_api(tgt=minion_id, arg=['pid=%s' % pid, 'attrs=["cmdline","status"]'])
                                                            # 当调用api失败的时候会返回false
                                                            if response_data is False:
                                                                app_log.append('\n应用停止命令后台出错_error(9)，请联系管理员\n')
                                                                result['result'] = app_log
                                                                return JsonResponse(result)
                                                            else:
                                                                # 返回的cmdline会根据命令中空格（文件名字里有空格不算）进行分割成列表，所以下面用空格合并列表
                                                                cmdline_result = ' '.join(response_data['return'][0][minion_id]['cmdline'])
                                                                if cmdline == cmdline_result:
                                                                    response_data = saltapi.ps_kill_pid_api(
                                                                        tgt=minion_id, arg=['pid=%s' % pid])
                                                                    if response_data is False:
                                                                        app_log.append(
                                                                            '\n应用停止命令后台出错_error(10)，请联系管理员\n')
                                                                        result['result'] = app_log
                                                                        return JsonResponse(result)
                                                                    else:
                                                                        if response_data['return'][0][minion_id]:
                                                                            app_log.append('\n' + '应用服务停止成功<-\n')
                                                                        else:
                                                                            app_log.append(
                                                                                '\n' + '应用停止在结束进程pid时返回结果为失败，系统默认为停止失败\n')
                                                                            result['result'] = app_log
                                                                            return JsonResponse(result)
                                                                else:
                                                                    app_log.append(
                                                                        '\n' + '应用停止在匹配命令行时没有发现可以匹配的命令行，系统默认为已经停止成功\n')

                                                    else:
                                                        app_log.append('\n'+'应用停止在查看进程时没有发现指定的进程，系统默认为已经停止成功\n')
                                                except Exception as e:
                                                    logger.error('应用服务停止代码出错：'+str(e))
                                                    app_log.append('\n' + '应用服务停止后台出错_error(11):' + str(e))
                                                    result['result'] = app_log
                                                    return JsonResponse(result)
                                elif 'supervisor_stop' in operation_arguments:
                                    stop_cmd = operation_arguments['supervisor_stop']
                                    with requests.Session() as s:
                                        saltapi = SaltAPI(session=s)
                                        if saltapi.get_token() is False:
                                            app_log.append('\n应用停止命令后台出错_error(12)，请联系管理员')
                                            result['result'] = app_log
                                            return JsonResponse(result)
                                        else:
                                            # 直接执行supervisor停止命令，只要不出现False，就执行查询状态命令，就看状态来决定成功与否
                                            response_data = saltapi.supervisord_stop_api(tgt=minion_id, arg=[stop_cmd])
                                            # 当调用api失败的时候会返回false
                                            if response_data is False:
                                                app_log.append('\n应用停止命令后台出错_error(13)，请联系管理员')
                                                result['result'] = app_log
                                                return JsonResponse(result)
                                            else:
                                                # 查看是否有supervisor名称存在，不支持模糊搜索
                                                response_data = saltapi.supervisord_status_api(tgt=minion_id, arg=[stop_cmd])
                                                # 当调用api失败的时候会返回false
                                                if response_data is False:
                                                    app_log.append('\n应用停止命令后台出错_error(14)，请联系管理员')
                                                    result['result'] = app_log
                                                    return JsonResponse(result)
                                                else:
                                                    try:
                                                        status_result = response_data['return'][0][minion_id][stop_cmd]['state']
                                                        # 这里有发现一个问题，返回的state值可能不是STOPPED可能是FATAL或者BACKOFF,所以判断只要不是RUNNING都算停止
                                                        if status_result == 'STOPPED':
                                                            app_log.append('\n' + '应用服务停止成功<-\n')
                                                        else:
                                                            if status_result != 'RUNNING':
                                                                app_log.append(
                                                                    '\n' + '返回的状态码为%s,只要不是RUNNING应用服务都默认为停止成功<-\n' % status_result)
                                                            else:
                                                                app_log.append('\n' + '应用停止查询状态结果为RUNNING，停止失败\n')
                                                                result['result'] = app_log
                                                                return JsonResponse(result)
                                                    except Exception as e:
                                                        logger.error('应用服务停止代码出错：' + str(e))
                                                        app_log.append('\n' + '应用停止结果有错，返回结果：' + str(response_data))
                                                        result['result'] = app_log
                                                        return JsonResponse(result)
                            elif operation == '应用启动':
                                app_log.append('\n\n开始执行应用启动操作->\n')
                                if '启动服务名' in operation_arguments:
                                    start_server_name = operation_arguments['启动服务名']
                                    with requests.Session() as s:
                                        saltapi = SaltAPI(session=s)
                                        if saltapi.get_token() is False:
                                            app_log.append('\n应用启动后台出错_error(0)，请联系管理员')
                                            result['result'] = app_log
                                            return JsonResponse(result)
                                        else:
                                            response_data = saltapi.service_available_api(tgt=minion_id, arg=[start_server_name])
                                            if response_data is False:
                                                app_log.append('\n应用启动后台出错_error(1)，请联系管理员')
                                                result['result'] = app_log
                                                return JsonResponse(result)
                                            else:
                                                if response_data['return'][0][minion_id] is False:
                                                    app_log.append('\n' + '应用启动失败,请确定是否存在该服务！！')
                                                    result['result'] = app_log
                                                    return JsonResponse(result)
                                                elif response_data['return'][0][minion_id] is True:
                                                    response_data = saltapi.service_start_api(tgt=minion_id, arg=[start_server_name])
                                                    # 当调用api失败的时候会返回false
                                                    if response_data is False:
                                                        app_log.append('\n应用启动后台出错_error(2)，请联系管理员')
                                                        result['result'] = app_log
                                                        return JsonResponse(result)
                                                    else:
                                                        start_data = response_data['return'][0][minion_id]
                                                        response_data = saltapi.service_status_api(tgt=minion_id,
                                                                                                   arg=[start_server_name])
                                                        # 当调用api失败的时候会返回false
                                                        if response_data is False:
                                                            app_log.append('\n应用启动后台出错_error(3)，请联系管理员')
                                                            result['result'] = app_log
                                                            return JsonResponse(result)
                                                        elif response_data['return'][0][minion_id] is False:
                                                            app_log.append('\n'+'应用启动失败。')
                                                            result['result'] = app_log
                                                            return JsonResponse(result)
                                                        elif response_data['return'][0][minion_id] is True:
                                                            app_log.append('\n'+'应用启动成功<-\n')
                                                        else:
                                                            app_log.append('\n'+'应用启动失败,执行结果：'+str(start_data)+str(response_data['return'][0][minion_id]))
                                                            result['result'] = app_log
                                                            return JsonResponse(result)
                                                else:
                                                    app_log.append('\n' + '应用启动失败查询服务时没有返回正确结果,执行结果：' + str(
                                                        response_data['return'][0][minion_id]))
                                                    result['result'] = app_log
                                                    return JsonResponse(result)
                                elif '启动命令' in operation_arguments:
                                    start_cmd = operation_arguments['启动命令']
                                    if sys_type == 'windows':
                                        start_cmd = start_cmd+'&& echo %errorlevel%'
                                        split_cmd = '\r\n'
                                    else:
                                        start_cmd = start_cmd + '; echo $?'
                                        split_cmd = '\n'
                                    with requests.Session() as s:
                                        saltapi = SaltAPI(session=s)
                                        if saltapi.get_token() is False:
                                            app_log.append('\n应用启动命令后台出错_error(3)，请联系管理员')
                                            result['result'] = app_log
                                            return JsonResponse(result)
                                        else:
                                            response_data = saltapi.cmd_run_api(tgt=minion_id, arg=[start_cmd,"shell='/bin/bash'","runas='root'"])
                                            # 当调用api失败的时候会返回false
                                            if response_data is False:
                                                app_log.append('\n应用启动命令后台出错_error(4)，请联系管理员')
                                                result['result'] = app_log
                                                return JsonResponse(result)
                                            else:
                                                try:
                                                    response_data = response_data['return'][0][minion_id].rsplit(split_cmd, 1)
                                                    # 发现有的命令没有输出那么最终只会有成功失败的0、1返回这时候列表长度就=1
                                                    if len(response_data) == 1:
                                                        if response_data[0] == '0':
                                                            app_log.append('\n' + '应用服务启动成功<-\n')
                                                        else:
                                                            app_log.append('\n' + '应用启动失败:' + response_data[0])
                                                            result['result'] = app_log
                                                            return JsonResponse(result)
                                                    else:
                                                        if response_data[1] == '0':
                                                            app_log.append('\n' + '应用服务启动成功<-\n')
                                                        else:
                                                            app_log.append('\n' + '应用启动失败:' + response_data[0])
                                                            result['result'] = app_log
                                                            return JsonResponse(result)
                                                except Exception as e:
                                                    app_log.append('\n' + '应用启动失败_error(5):' + str(response_data))
                                                    result['result'] = app_log
                                                    return JsonResponse(result)
                                elif '任务计划启动' in operation_arguments:
                                    start_cmd = operation_arguments['任务计划启动']
                                    if sys_type == 'linux':
                                        logger.error('应用启动失败，应用启动中《任务计划启动》启动方式只适用于windows')
                                        app_log.append('\n\n应用启动失败，应用启动中《任务计划启动》启动方式只适用于windows')
                                        result['result'] = app_log
                                        return JsonResponse(result)
                                    with requests.Session() as s:
                                        saltapi = SaltAPI(session=s)
                                        if saltapi.get_token() is False:
                                            app_log.append('\n应用启动命令后台出错_error(6)，请联系管理员')
                                            result['result'] = app_log
                                            return JsonResponse(result)
                                        else:
                                            response_data = saltapi.task_run_api(tgt=minion_id, arg=[start_cmd])
                                            # 当调用api失败的时候会返回false
                                            if response_data is False:
                                                app_log.append('\n应用启动命令后台出错_error(7)，请联系管理员')
                                                result['result'] = app_log
                                                return JsonResponse(result)
                                            else:
                                                try:
                                                    response_data = response_data['return'][0][minion_id]
                                                    if response_data is True:
                                                        app_log.append('\n' + '应用启动成功<-\n')
                                                    else:
                                                        app_log.append('\n'+'应用启动失败:'+response_data)
                                                        result['result'] = app_log
                                                        return JsonResponse(result)
                                                except Exception as e:
                                                    app_log.append('\n' + '应用启动后台出错_error(8):' + str(e))
                                                    result['result'] = app_log
                                                    return JsonResponse(result)
                                elif 'supervisor_start' in operation_arguments:
                                    stop_cmd = operation_arguments['supervisor_start']
                                    with requests.Session() as s:
                                        saltapi = SaltAPI(session=s)
                                        if saltapi.get_token() is False:
                                            app_log.append('\n应用启动命令后台出错_error(9)，请联系管理员')
                                            result['result'] = app_log
                                            return JsonResponse(result)
                                        else:
                                            # 直接执行supervisor启动命令，只要不出现False，就执行查询状态命令，就看状态来决定成功与否
                                            response_data = saltapi.supervisord_start_api(tgt=minion_id, arg=[stop_cmd])
                                            # 当调用api失败的时候会返回false
                                            if response_data is False:
                                                app_log.append('\n应用启动命令后台出错_error(10)，请联系管理员')
                                                result['result'] = app_log
                                                return JsonResponse(result)
                                            else:
                                                # 查看是否有supervisor名称存在，不支持模糊搜索
                                                response_data = saltapi.supervisord_status_api(tgt=minion_id, arg=[stop_cmd])
                                                # 当调用api失败的时候会返回false
                                                if response_data is False:
                                                    app_log.append('\n应用启动命令后台出错_error(11)，请联系管理员')
                                                    result['result'] = app_log
                                                    return JsonResponse(result)
                                                else:
                                                    try:
                                                        status_result = response_data['return'][0][minion_id][stop_cmd]['state']
                                                        if status_result == 'RUNNING':
                                                            app_log.append('\n' + '应用启动成功<-\n')
                                                        else:
                                                            app_log.append('\n' + '应用启动查询状态结果有错，返回结果：'+str(response_data))
                                                            result['result'] = app_log
                                                            return JsonResponse(result)
                                                    except Exception as e:
                                                        logger.error('应用服务启动代码出错：' + str(e))
                                                        app_log.append('\n' + '应用启动结果有错，返回结果：' + str(response_data))
                                                        result['result'] = app_log
                                                        return JsonResponse(result)
                            elif operation == '执行命令1':
                                execute_cmd = operation_arguments['执行命令1']
                                if sys_type == 'windows':
                                    execute_cmd = execute_cmd + '&& echo %errorlevel%'
                                    split_cmd = '\r\n'
                                else:
                                    execute_cmd = execute_cmd + '; echo $?'
                                    split_cmd = '\n'
                                with requests.Session() as s:
                                    saltapi = SaltAPI(session=s)
                                    if saltapi.get_token() is False:
                                        app_log.append('\n执行命令1后台出错_error(0)，请联系管理员')
                                        result['result'] = app_log
                                        return JsonResponse(result)
                                    else:
                                        response_data = saltapi.cmd_run_api(tgt=minion_id, arg=[execute_cmd,"shell='/bin/bash'","runas='root'"])
                                        # 当调用api失败的时候会返回false
                                        if response_data is False:
                                            app_log.append('\n执行命令1后台出错_error(1)，请联系管理员')
                                            result['result'] = app_log
                                            return JsonResponse(result)
                                        else:
                                            try:
                                                response_data = response_data['return'][0][minion_id].rsplit(split_cmd, 1)
                                                # 发现有的命令没有输出那么最终只会有成功失败的0、1返回这时候列表长度就=1
                                                if len(response_data) == 1:
                                                    if response_data[0] == '0':
                                                        app_log.append('\n' + '执行命令1成功<-\n')
                                                    else:
                                                        app_log.append('\n' + '执行命令1失败:' + response_data[0])
                                                        result['result'] = app_log
                                                        return JsonResponse(result)
                                                else:
                                                    if response_data[1] == '0':
                                                        app_log.append('\n' + '执行命令1成功<-\n')
                                                    else:
                                                        app_log.append('\n' + '执行命令1失败:' + response_data[0])
                                                        result['result'] = app_log
                                                        return JsonResponse(result)
                                            except Exception as e:
                                                app_log.append('\n' + '执行命令1失败_error(2):' + str(response_data))
                                                result['result'] = app_log
                                                return JsonResponse(result)
                            elif operation == '执行命令2':
                                execute_cmd = operation_arguments['执行命令2']
                                if sys_type == 'windows':
                                    execute_cmd = execute_cmd + '&& echo %errorlevel%'
                                    split_cmd = '\r\n'
                                else:
                                    execute_cmd = execute_cmd + '; echo $?'
                                    split_cmd = '\n'
                                with requests.Session() as s:
                                    saltapi = SaltAPI(session=s)
                                    if saltapi.get_token() is False:
                                        app_log.append('\n执行命令2后台出错_error(0)，请联系管理员')
                                        result['result'] = app_log
                                        return JsonResponse(result)
                                    else:
                                        response_data = saltapi.cmd_run_api(tgt=minion_id, arg=[execute_cmd,"shell='/bin/bash'","runas='root'"])
                                        # 当调用api失败的时候会返回false
                                        if response_data is False:
                                            app_log.append('\n执行命令2后台出错_error(1)，请联系管理员')
                                            result['result'] = app_log
                                            return JsonResponse(result)
                                        else:
                                            try:
                                                response_data = response_data['return'][0][minion_id].rsplit(split_cmd, 1)
                                                # 发现有的命令没有输出那么最终只会有成功失败的0、1返回这时候列表长度就=1
                                                if len(response_data) == 1:
                                                    if response_data[0] == '0':
                                                        app_log.append('\n' + '执行命令2成功<-\n')
                                                    else:
                                                        app_log.append('\n' + '执行命令2失败:' + response_data[0])
                                                        result['result'] = app_log
                                                        return JsonResponse(result)
                                                else:
                                                    if response_data[1] == '0':
                                                        app_log.append('\n' + '执行命令2成功<-\n')
                                                    else:
                                                        app_log.append('\n' + '执行命令2失败:' + response_data[0])
                                                        result['result'] = app_log
                                                        return JsonResponse(result)
                                            except Exception as e:
                                                app_log.append('\n' + '执行命令2失败_error(2):' + str(response_data))
                                                result['result'] = app_log
                                                return JsonResponse(result)

                        app_log.append(('-' * 10 + ('Minion_ID:%s发布完成 时间戳%s' % (minion_id, time.strftime('%X')))+'-'*10).center(88) + '\n\n\n\n\n\n')
                    result['status'] = True
                    result['result'] = app_log
                    return JsonResponse(result)
                except Exception as e:
                    logger.error(str(e))
                    result['result'] = app_log
                    result['result'].append('\n出错了：'+str(e))
                    return JsonResponse(result)
                finally:
                    if result['status']:
                        release_result = '发布成功'
                        if 'SVN更新' in operation_content:
                            AppRelease.objects.filter(app_name=app_name).update(app_svn_version_success=app_svn_version_success)
                    else:
                        release_result = '发布失败'
                    username = request.user.username
                    AppReleaseLog.objects.create(app_name=app_name, log_content=app_log, release_result=release_result, username=username)
                    AppRelease.objects.filter(app_name=app_name).update(update_time=time.strftime('%Y年%m月%d日 %X'))
            elif request.POST.get('app_tag_key') == 'app_backup':
                app_name = request.POST.get('app_name')
                try:
                    app_backup_path = AppRelease.objects.get(app_name=app_name).app_backup_path
                    app_path = AppRelease.objects.get(app_name=app_name).app_path
                    minion_id = AppRelease.objects.get(app_name=app_name).minion_id
                    minion_id_list = minion_id.split(',')
                    app_log.append(('-' * 20 + ('Minion_ID:%s 备份任务启动' % minion_id) + '-' * 20).center(88) + '\n')
                    app_log.append('\n\n开始备份->\n')
                    with requests.Session() as s:
                        saltapi = SaltAPI(session=s)
                        if saltapi.get_token() is False:
                            app_log.append('\n备份应用后台出错_error(0)，请联系管理员')
                            result['result'] = app_log
                            return JsonResponse(result)
                        else:
                            # 判断客户端应用目录是否存在，存在也要删除
                            for minion in minion_id_list:
                                response_data = saltapi.file_directory_exists_api(tgt=minion, arg=[app_path])
                                # 当调用api失败的时候会返回false
                                if response_data is False:
                                    app_log.append('\n备份应用后台出错_error(1)，请联系管理员')
                                    result['result'] = app_log
                                    return JsonResponse(result)
                                else:
                                    response_data = response_data['return'][0][minion]
                                    if response_data is True:
                                        response_data = saltapi.state_api(tgt=minion_id, arg=["copy_dir", "pillar={'source_path':'%s','name_path':'%s'}" % (app_path, app_backup_path), "concurrent=True"])
                                        if response_data is False:
                                            app_log.append('\n备份应用后台出错_error(2)，请联系管理员')
                                            result['result'] = app_log
                                            return JsonResponse(result)
                                        else:
                                            format_result = format_state(response_data)
                                            # 这个是对格式化输出的一个判断，类型str说明格式化出错了呵呵，一般在minion一个sls未执行完成又执行会出现
                                            if type(format_result) == str:
                                                # 如果minion客户端停了会返回：{'return': [{'192.168.100.170': False}]}
                                                app_log.append(format_result)
                                                app_log.append('\n' + '备份应用失败！！')
                                                result['result'] = app_log
                                                return JsonResponse(result)
                                            else:
                                                try:
                                                    failed_result = re.search(r'Failed:     (\d+)', format_result[0]).group(1)
                                                    if int(failed_result) != 0:
                                                        app_log.extend(format_result)
                                                        app_log.append('\n' + '备份应用失败！！')
                                                        result['result'] = app_log
                                                        return JsonResponse(result)
                                                except Exception as e:
                                                    app_log.append('\n' + '备份应用代码出错：'+str(e))
                                                    result['result'] = app_log
                                                    return JsonResponse(result)
                                            app_log.extend(format_result)
                                            app_log.append('\n备份应用完成<-\n\n')
                                    else:
                                        app_log.append('\n备份应用失败,应用目录不存在，无法备份，请确认是否发布过')
                                        result['result'] = app_log
                                        return JsonResponse(result)
                            app_log.append(
                                ('-' * 20 + ('Minion_ID:%s备份任务结束' % minion_id) + '-' * 20).center(88) + '\n\n\n\n\n\n')
                    result['status'] = True
                    result['result'] = app_log
                    return JsonResponse(result)
                except Exception as e:
                    logger.error(str(e))
                    result['result'] = app_log
                    result['result'].append('\n出错了：' + str(e))
                    return JsonResponse(result)
                finally:
                    if result['status']:
                        release_result = '备份成功'
                    else:
                        release_result = '备份失败'
                    username = request.user.username
                    AppReleaseLog.objects.create(app_name=app_name, log_content=app_log, release_result=release_result, username=username)
                    AppRelease.objects.filter(app_name=app_name).update(update_time=time.strftime('%Y年%m月%d日 %X'))
            elif request.POST.get('app_tag_key') == 'app_restore':
                app_name = request.POST.get('app_name')
                try:
                    app_backup_path = AppRelease.objects.get(app_name=app_name).app_backup_path
                    app_path = AppRelease.objects.get(app_name=app_name).app_path
                    minion_id = AppRelease.objects.get(app_name=app_name).minion_id
                    minion_id_list = minion_id.split(',')
                    app_log.append(('-' * 20 + ('Minion_ID:%s 还原任务启动' % minion_id) + '-' * 20).center(88) + '\n')
                    app_log.append('\n\n开始还原->\n')
                    with requests.Session() as s:
                        saltapi = SaltAPI(session=s)
                        if saltapi.get_token() is False:
                            app_log.append('\n还原应用后台出错_error(0)，请联系管理员')
                            result['result'] = app_log
                            return JsonResponse(result)
                        else:
                            # 判断客户端应用目录是否存在，存在也要删除
                            for minion in minion_id_list:
                                response_data = saltapi.file_directory_exists_api(tgt=minion, arg=[app_backup_path])
                                # 当调用api失败的时候会返回false
                                if response_data is False:
                                    app_log.append('\n还原应用后台出错_error(1)，请联系管理员')
                                    result['result'] = app_log
                                    return JsonResponse(result)
                                else:
                                    response_data = response_data['return'][0][minion]
                                    if response_data is True:
                                        response_data = saltapi.state_api(tgt=minion_id, arg=["copy_dir", "pillar={'source_path':'%s','name_path':'%s'}" % (app_backup_path, app_path), "concurrent=True"])
                                        if response_data is False:
                                            app_log.append('\n还原应用后台出错_error(2)，请联系管理员')
                                            result['result'] = app_log
                                            return JsonResponse(result)
                                        else:
                                            format_result = format_state(response_data)
                                            # 这个是对格式化输出的一个判断，类型str说明格式化出错了呵呵，一般在minion一个sls未执行完成又执行会出现
                                            if type(format_result) == str:
                                                # 如果minion客户端停了会返回：{'return': [{'192.168.100.170': False}]}
                                                app_log.append(format_result)
                                                app_log.append('\n' + '还原应用失败！！')
                                                result['result'] = app_log
                                                return JsonResponse(result)
                                            else:
                                                try:
                                                    failed_result = re.search(r'Failed:     (\d+)', format_result[0]).group(1)
                                                    if int(failed_result) != 0:
                                                        app_log.extend(format_result)
                                                        app_log.append('\n' + '还原应用失败！！')
                                                        result['result'] = app_log
                                                        return JsonResponse(result)
                                                except Exception as e:
                                                    app_log.append('\n' + '还原应用代码出错：'+str(e))
                                                    result['result'] = app_log
                                                    return JsonResponse(result)
                                            app_log.extend(format_result)
                                            app_log.append('\n还原应用完成<-\n\n')
                                    else:
                                        app_log.append('\n还原应用失败,应用备份目录不存在，无法还原，请确认是否备份过')
                                        result['result'] = app_log
                                        return JsonResponse(result)
                            app_log.append(
                                ('-' * 20 + ('Minion_ID:%s还原任务结束' % minion_id) + '-' * 20).center(88) + '\n\n\n\n\n\n')
                    result['status'] = True
                    result['result'] = app_log
                    return JsonResponse(result)
                except Exception as e:
                    logger.error(str(e))
                    result['result'] = app_log
                    result['result'].append('\n出错了：' + str(e))
                    return JsonResponse(result)
                finally:
                    if result['status']:
                        release_result = '还原成功'
                    else:
                        release_result = '还原失败'
                    username = request.user.username
                    AppReleaseLog.objects.create(app_name=app_name, log_content=app_log, release_result=release_result, username=username)
                    AppRelease.objects.filter(app_name=app_name).update(update_time=time.strftime('%Y年%m月%d日 %X'))
            else:
                result['result'] = '应用发布页ajax提交了错误的tag'
                return JsonResponse(result)
    except Exception as e:
        logger.error('应用发布页ajax提交处理有问题', e)
        result['result'] = '应用发布页ajax提交处理有问题'
        return JsonResponse(result)


# 发布系统 应用发布组 主
def app_group(request):
    try:
        if request.method == 'GET':
            # 默认如果没有get到的话值为None，这里我需要为空''，所以下面修改默认值为''
            search_field = request.GET.get('search_field', '')
            search_content = request.GET.get('search_content', '')
            if request.user.is_superuser:
                if search_content is '':
                    app_group_data = AppGroup.objects.all().order_by('id')
                    data_list = getPage(request, app_group_data, 12)
                else:
                    if search_field == 'search_app_group_name':
                        app_data = AppGroup.objects.filter(
                            app_group_name__icontains=search_content).order_by(
                            'id')
                        data_list = getPage(request, app_data, 12)
                    elif search_field == 'search_app_group_members':
                        app_data = AppGroup.objects.filter(
                            app_group_members__icontains=search_content).order_by(
                            'id')
                        data_list = getPage(request, app_data, 12)
                    else:
                        data_list = ""
                return render(request, 'release_sys/app_group.html',
                              {'data_list': data_list, 'search_field': search_field, 'search_content': search_content})
            else:
                username = request.user.username
                try:
                    app_auth_app_group_data = AppAuth.objects.get(username=username).app_group_perms.split(',')
                except Exception as e:
                    app_auth_app_group_data = ''
                if search_content is '':
                    app_group_data = AppGroup.objects.filter(app_group_name__in=app_auth_app_group_data).order_by('id')
                    data_list = getPage(request, app_group_data, 12)
                else:
                    if search_field == 'search_app_group_name':
                        app_data = AppGroup.objects.filter(app_group_name__in=app_auth_app_group_data).filter(
                            app_group_name__icontains=search_content).order_by(
                            'id')
                        data_list = getPage(request, app_data, 12)
                    elif search_field == 'search_app_group_members':
                        app_data = AppGroup.objects.filter(app_group_name__in=app_auth_app_group_data).filter(
                            app_group_members__icontains=search_content).order_by(
                            'id')
                        data_list = getPage(request, app_data, 12)
                    else:
                        data_list = ""
                return render(request, 'release_sys/app_group.html',
                              {'data_list': data_list, 'search_field': search_field, 'search_content': search_content})
    except Exception as e:
        logger.error('应用发布组页面有问题', e)
        return render(request, 'release_sys/app_group.html')


# 发布系统 应用发布组 成员管理页 主
def app_group_members_manage(request):
    try:
        if request.method == 'GET':
            app_group_name = request.GET.get('app_group_name')
            app_group_members_data = AppGroup.objects.get(app_group_name=app_group_name).app_group_members
            app_data = []
            if app_group_members_data:
                for app_name in app_group_members_data.split(','):
                    app_data.extend(AppRelease.objects.filter(app_name=app_name))
            # 下面这个app_data_list的作用是复制一份，因为刚开始下面做判断的时候直接用for  app in app_data然后内
            # 部又用了app_data.remove这样会导致app_data变了连锁导致开头for出现奇怪的现象逻辑上面自己搞错了
            app_data_list = app_data[:]
            search_field = request.GET.get('search_field', '')
            search_content = request.GET.get('search_content', '')
            if search_content is '':
                data_list = getPage(request, app_data_list, 12)
            else:
                if search_field == 'search_app_name':
                    for app in app_data:
                        if search_content in app.app_name:
                            pass
                        else:
                            app_data_list.remove(app)
                    data_list = getPage(request, app_data_list, 12)
                elif search_field == 'search_minion_id':
                    for app in app_data:
                        if search_content in app.minion_id:
                            pass
                        else:
                            app_data_list.remove(app)
                    data_list = getPage(request, app_data_list, 12)
                else:
                    data_list = ""
            return render(request, 'release_sys/app_group_members_manage.html',
                          {'data_list': data_list, 'search_field': search_field,
                           'search_content': search_content,
                           'app_group_name': app_group_name,
                           'app_group_members_data': app_group_members_data})
    except Exception as e:
        logger.error('成员管理页面有问题', e)
        return render(request, 'release_sys/app_group_members_manage.html')


# 发布系统 应用发布组 ajax提交处理
def app_group_ajax(request):
    result = {'result': None, 'status': False}
    app_log = []
    try:
        if request.is_ajax():
            # 在ajax提交时候多一个字段作为标识，来区分多个ajax提交哈，厉害！
            if request.POST.get('app_group_tag_key') == 'app_group_add' and request.user.is_superuser:
                obj = AppGroupAddForm(request.POST)
                if obj.is_valid():
                    AppGroup.objects.create(app_group_name=obj.cleaned_data["app_group_name"], description=obj.cleaned_data["description"])
                    result['result'] = '成功'
                    result['status'] = True
                else:
                    error_str = obj.errors.as_json()
                    result['result'] = json.loads(error_str)
                return JsonResponse(result)
            elif request.GET.get('app_group_tag_key') == 'modal_search_app_name':

                app_name = request.GET.get('app_name')
                app_name_list = AppRelease.objects.filter(app_name__icontains=app_name).order_by(
                    'create_time').values_list('app_name', flat=True)
                result['result'] = list(app_name_list)
                result['status'] = True
                return JsonResponse(result)
            elif request.POST.get('app_group_tag_key') == 'app_group_update' and request.user.is_superuser:
                obj = AppGroupUpdateForm(request.POST)
                if obj.is_valid():
                    AppGroup.objects.filter(app_group_name=obj.cleaned_data["app_group_name"]).update(
                        description=obj.cleaned_data["description"])
                    result['result'] = '成功'
                    result['status'] = True
                else:
                    error_str = obj.errors.as_json()
                    result['result'] = json.loads(error_str)
                return JsonResponse(result)
            elif request.POST.get('app_group_tag_key') == 'app_group_delete' and request.user.is_superuser:
                app_group_name = request.POST.get('app_group_name')
                try:
                    AppGroup.objects.filter(app_group_name=app_group_name).delete()
                    result['result'] = '成功'
                    result['status'] = True
                except Exception as e:
                    result['result'] = str(e)
                return JsonResponse(result)
            elif request.POST.get('app_group_tag_key') == 'app_group_member_add' and request.user.is_superuser:
                obj = AppGroupUpdateForm(request.POST)
                if obj.is_valid():
                    AppGroup.objects.filter(app_group_name=obj.cleaned_data["app_group_name"]).update(
                        app_group_members=obj.cleaned_data["app_group_members"])
                else:
                    error_str = obj.errors.as_json()
                    result['result'] = json.loads(error_str)
                    return JsonResponse(result)
                result['result'] = '成功'
                result['status'] = True
                return JsonResponse(result)
            elif request.POST.get('app_group_tag_key') == 'app_group_member_delete' and request.user.is_superuser:
                app_name = request.POST.get('app_name')
                app_group_name = request.POST.get('app_group_name')
                try:
                    app_group_members = AppGroup.objects.get(app_group_name=app_group_name).app_group_members
                    app_group_members_list = app_group_members.split(',')
                    app_group_members_list.remove(app_name)
                    app_group_members = ','.join(app_group_members_list)
                    AppGroup.objects.filter(app_group_name=app_group_name).update(app_group_members=app_group_members)
                    result['result'] = '成功'
                    result['status'] = True
                except Exception as e:
                    result['result'] = str(e)
                return JsonResponse(result)
            else:
                result['result'] = '应用发布组ajax提交了错误的tag'
                return JsonResponse(result)
    except Exception as e:
        logger.error('应用发布组ajax提交处理有问题', e)
        result['result'] = '应用发布组ajax提交处理有问题'
        return JsonResponse(result)


# 发布系统 应用授权 主
def app_auth(request):
    try:
        if request.method == 'GET':
            # 默认如果没有get到的话值为None，这里我需要为空''，所以下面修改默认值为''
            search_field = request.GET.get('search_field', '')
            search_content = request.GET.get('search_content', '')
            username_list = list(AppAuth.objects.values('my_user_id', 'username'))
            if search_content is '':
                app_auth_data = AppAuth.objects.all().order_by('my_user_id')
                data_list = getPage(request, app_auth_data, 12)
            else:
                if search_field == 'search_myuser_username':
                    app_auth_data = AppAuth.objects.filter(username__icontains=search_content).order_by('my_user_id')
                    data_list = getPage(request, app_auth_data, 12)
                elif search_field == 'search_app_name':
                    app_auth_data = AppAuth.objects.filter(app_perms__icontains=search_content).order_by('my_user_id')
                    data_list = getPage(request, app_auth_data, 12)
                elif search_field == 'search_app_group_name':
                    app_auth_data = AppAuth.objects.filter(app_group_perms__icontains=search_content).order_by('my_user_id')
                    data_list = getPage(request, app_auth_data, 12)
                else:
                    data_list = ""
            return render(request, 'release_sys/app_auth.html',
                          {'data_list': data_list, 'search_field': search_field, 'search_content': search_content,
                           'username_list': username_list})
    except Exception as e:
        logger.error('应用授权页面有问题', e)
        return render(request, 'release_sys/app_auth.html')


# 发布系统 应用授权 应用权限管理页
def app_auth_app_manage(request):
    try:
        if request.method == 'GET':
            my_user_id = request.GET.get('my_user_id')
            username = request.GET.get('username')
            app_perms_data = AppAuth.objects.get(username=username).app_perms
            if app_perms_data:
                app_data_list = AppRelease.objects.filter(app_name__in=app_perms_data.split(',')).order_by('app_name')
            else:
                app_data_list = []
            # 默认如果没有get到的话值为None，这里我需要为空''，所以下面修改默认值为''
            search_field = request.GET.get('search_field', '')
            search_content = request.GET.get('search_content', '')
            if search_content is '':
                data_list = getPage(request, app_data_list, 12)
            else:
                if search_field == 'search_app_name':
                    app_data_list = app_data_list.filter(app_name__icontains=search_content)
                    data_list = getPage(request, app_data_list, 12)
                elif search_field == 'search_minion_id':
                    app_data_list = app_data_list.filter(minion_id__icontains=search_content)
                    data_list = getPage(request, app_data_list, 12)
                else:
                    data_list = ""
            return render(request, 'release_sys/app_auth_app_manage.html', {'data_list': data_list, 'search_field': search_field,
                                                                'search_content': search_content, 'username': username,
                                                                'app_perms_data': app_perms_data, 'my_user_id': my_user_id})
    except Exception as e:
        logger.error('应用授权应用权限管理页面有问题', e)
        return render(request, 'release_sys/app_auth_app_manage.html')


# 发布系统 应用授权 应用组权限管理页
def app_auth_app_group_manage(request):
    try:
        if request.method == 'GET':
            my_user_id = request.GET.get('my_user_id')
            username = request.GET.get('username')
            app_group_perms_data = AppAuth.objects.get(username=username).app_group_perms
            if app_group_perms_data:
                app_data_list = AppGroup.objects.filter(app_group_name__in=app_group_perms_data.split(',')).order_by('id')
            else:
                app_data_list = []
            # 默认如果没有get到的话值为None，这里我需要为空''，所以下面修改默认值为''
            search_field = request.GET.get('search_field', '')
            search_content = request.GET.get('search_content', '')
            if search_content is '':
                data_list = getPage(request, app_data_list, 12)
            else:
                if search_field == 'search_app_group_name':
                    app_data_list = app_data_list.filter(app_group_name__icontains=search_content).order_by('id')
                    data_list = getPage(request, app_data_list, 12)
                elif search_field == 'search_app_group_members':
                    app_data_list = app_data_list.filter(app_group_members__icontains=search_content).order_by('id')
                    data_list = getPage(request, app_data_list, 12)
                else:
                    data_list = ""
            return render(request, 'release_sys/app_auth_app_group_manage.html', {'data_list': data_list,
                                                                      'search_field': search_field,
                                                                      'search_content': search_content,
                                                                      'username': username,
                                                                      'app_group_perms_data': app_group_perms_data,
                                                                      'my_user_id': my_user_id})
    except Exception as e:
        logger.error('应用授权应用组权限管理页面有问题', e)
        return render(request, 'release_sys/app_auth_app_group_manage.html')


# 发布系统 应用授权 ajax提交处理
def app_auth_ajax(request):
    result = {'result': None, 'status': False}
    try:
        if request.is_ajax():
            if request.POST.get('app_auth_tag_key') == 'app_auth_add':
                username_list = request.POST.get('username_list').split(',')
                for id_and_username in username_list:
                    id_and_username = id_and_username.split(' ')
                    data = {'my_user_id': id_and_username[0], 'username': id_and_username[1]}
                    obj = AppAuthCreateForm(data)
                    if obj.is_valid():
                        AppAuth.objects.create(my_user_id=obj.cleaned_data["my_user_id"], username=obj.cleaned_data["username"])
                        result['result'] = '成功'
                        result['status'] = True
                    else:
                        error_str = obj.errors.as_json()
                        result['result'] = json.loads(error_str)
                        return JsonResponse(result)
                return JsonResponse(result)
            elif request.GET.get('app_auth_tag_key') == 'modal_search_username':
                username = request.GET.get('username')
                username_list = MyUser.objects.filter(username__icontains=username).order_by('id').values('id', 'username')
                result['result'] = list(username_list)
                result['status'] = True
                return JsonResponse(result)
            elif request.GET.get('app_auth_tag_key') == 'modal_search_app_name':
                app_name = request.GET.get('app_name')
                app_name_list = AppRelease.objects.filter(app_name__icontains=app_name).order_by(
                    'create_time').values_list('app_name', flat=True)
                result['result'] = list(app_name_list)
                result['status'] = True
                return JsonResponse(result)
            elif request.GET.get('app_auth_tag_key') == 'modal_search_app_group':
                app_group_name = request.GET.get('app_group_name')
                app_group_list = AppGroup.objects.filter(app_group_name__icontains=app_group_name).order_by(
                    'id').values_list('app_group_name', flat=True)
                result['result'] = list(app_group_list)
                result['status'] = True
                return JsonResponse(result)
            elif request.POST.get('app_auth_tag_key') == 'app_auth_update':
                obj = AppAuthUpdateForm(request.POST)
                if obj.is_valid():
                    AppAuth.objects.filter(my_user_id=obj.cleaned_data['my_user_id'],
                                           username=obj.cleaned_data["username"]).update(
                        app_perms=obj.cleaned_data["app_perms"], app_group_perms=obj.cleaned_data["app_group_perms"])
                    result['result'] = '成功'
                    result['status'] = True
                else:
                    error_str = obj.errors.as_json()
                    result['result'] = json.loads(error_str)
                return JsonResponse(result)
            elif request.POST.get('app_auth_tag_key') == 'app_auth_description_update':
                obj = AppAuthUpdateForm(request.POST)
                if obj.is_valid():
                    AppAuth.objects.filter(my_user_id=obj.cleaned_data['my_user_id'],
                                           username=obj.cleaned_data["username"]).update(description=obj.cleaned_data["description"])
                    result['result'] = '成功'
                    result['status'] = True
                else:
                    error_str = obj.errors.as_json()
                    result['result'] = json.loads(error_str)
                return JsonResponse(result)
            elif request.POST.get('app_auth_tag_key') == 'app_auth_app_update':
                obj = AppAuthUpdateForm(request.POST)
                if obj.is_valid():
                    AppAuth.objects.filter(my_user_id=obj.cleaned_data['my_user_id'],
                                           username=obj.cleaned_data["username"]).update(
                        app_perms=obj.cleaned_data["app_perms"])
                    result['result'] = '成功'
                    result['status'] = True
                else:
                    error_str = obj.errors.as_json()
                    result['result'] = json.loads(error_str)
                return JsonResponse(result)
            elif request.POST.get('app_auth_tag_key') == 'app_auth_app_delete':
                username = request.POST.get('username')
                my_user_id = request.POST.get('my_user_id')
                app_name = request.POST.get('app_name')
                try:
                    app_perms = AppAuth.objects.get(my_user_id=my_user_id, username=username).app_perms
                    app_perms_list = app_perms.split(',')
                    # 为了结合单个移除和批量移除，对传过来的app_name做列表化因为批量删除就是逗号隔开的字符串，然后移除操作
                    for data in app_name.split(','):
                        app_perms_list.remove(data) if data in app_perms_list else app_perms_list
                    logger.error(app_perms_list)
                    app_perms = ','.join(app_perms_list)
                    AppAuth.objects.filter(my_user_id=my_user_id, username=username).update(app_perms=app_perms)
                    result['result'] = '成功'
                    result['status'] = True
                except Exception as e:
                    result['result'] = str(e)
                return JsonResponse(result)
            elif request.POST.get('app_auth_tag_key') == 'app_auth_app_group_update':
                obj = AppAuthUpdateForm(request.POST)
                if obj.is_valid():
                    AppAuth.objects.filter(my_user_id=obj.cleaned_data['my_user_id'],
                                           username=obj.cleaned_data["username"]).update(
                        app_group_perms=obj.cleaned_data["app_group_perms"])
                    result['result'] = '成功'
                    result['status'] = True
                else:
                    error_str = obj.errors.as_json()
                    result['result'] = json.loads(error_str)
                return JsonResponse(result)
            elif request.POST.get('app_auth_tag_key') == 'app_auth_app_group_delete':
                username = request.POST.get('username')
                my_user_id = request.POST.get('my_user_id')
                app_group_name = request.POST.get('app_group_name')
                try:
                    app_group_perms = AppAuth.objects.get(my_user_id=my_user_id, username=username).app_group_perms
                    app_group_perms_list = app_group_perms.split(',')
                    # 为了结合单个移除和批量移除，对传过来的app_name做列表化因为批量删除就是逗号隔开的字符串，然后移除操作
                    for data in app_group_name.split(','):
                        app_group_perms_list.remove(data) if data in app_group_perms_list else app_group_perms_list
                    app_group_perms = ','.join(app_group_perms_list)
                    AppAuth.objects.filter(my_user_id=my_user_id, username=username).update(app_group_perms=app_group_perms)
                    result['result'] = '成功'
                    result['status'] = True
                except Exception as e:
                    result['result'] = str(e)
                return JsonResponse(result)
            elif request.POST.get('app_auth_tag_key') == 'app_auth_delete':
                my_user_id = request.POST.get('my_user_id')
                try:
                    AppAuth.objects.filter(my_user_id=my_user_id).delete()
                    result['result'] = '成功'
                    result['status'] = True
                except Exception as e:
                    result['result'] = str(e)
                return JsonResponse(result)
            else:
                result['result'] = '应用发布组ajax提交了错误的tag'
                return JsonResponse(result)
    except Exception as e:
        logger.error('应用发布组ajax提交处理有问题', e)
        result['result'] = '应用发布组ajax提交处理有问题'
        return JsonResponse(result)


# 发布系统 应用发布 主
def app_release_test(request):
    try:
        if request.method == 'GET':
            # 默认如果没有get到的话值为None，这里我需要为空''，所以下面修改默认值为''
            search_field = request.GET.get('search_field', '')
            search_content = request.GET.get('search_content', '')
            if search_content is '':
                app_data = AppRelease.objects.all().order_by('create_time')
                data_list = getPage(request, app_data, 15)
            else:
                if search_field == 'search_app_name':
                    app_data = AppRelease.objects.filter(
                        app_name__icontains=search_content).order_by(
                        'create_time')
                    data_list = getPage(request, app_data, 15)
                elif search_field == 'search_minion_id':
                    app_data = AppRelease.objects.filter(
                        minion_id__icontains=search_content).order_by(
                        'create_time')
                    data_list = getPage(request, app_data, 15)
                elif search_field == 'search_svn_url':
                    app_data = AppRelease.objects.filter(
                        app_svn_url__icontains=search_content).order_by(
                        'create_time')
                    data_list = getPage(request, app_data, 15)
                else:
                    data_list = ""
            return render(request, 'release_sys/app_release_test.html',
                          {'data_list': data_list, 'search_field': search_field,
                       'search_content': search_content})
    except Exception as e:
        logger.error('应用发布页面有问题:'+str(e))
        return render(request, 'release_sys/app_release_test.html')