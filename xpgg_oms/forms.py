from django import forms
from .models import *
from django.core.exceptions import ValidationError
import re
import logging
# Create your views here.
logger = logging.getLogger('xpgg_oms.views')


# 发布系统 应用发布 表单验证 验证minion_id合法性
def app_release_minion_id_validate(value):
    for minion_id in value.split(','):
        check_minion_id = MinionList.objects.filter(minion_id=minion_id).count()
        if check_minion_id == 0:
            raise ValidationError('Minion列表中中没有该minion_id的记录')


# 发布系统 应用发布 表单验证 验证应用名称是否重复
def app_release_name_validate(value):
    is_app_name_exist = AppRelease.objects.filter(app_name=value).exists()
    if is_app_name_exist:
        raise ValidationError('应用名称已存在，请更换')


# 发布系统 应用发布  新增应用表单验证 主
class AppReleaseAddForm(forms.Form):
    app_name = forms.CharField(max_length=100, error_messages={'required': '应用名称不能为空', 'max_length': '最多100位'}, validators=[app_release_name_validate])
    sys_type = forms.CharField(error_messages={'required': '系统类型不能为空'})
    minion_id = forms.CharField(validators=[app_release_minion_id_validate], error_messages={'required': 'Minion_ID不能为空'})
    app_path = forms.CharField(max_length=200, error_messages={'required': '应用目录不能为空', 'max_length': '最多200位'})
    app_path_owner = forms.CharField(max_length=20, error_messages={'required': '应用目录属主不能为空', 'max_length': '最多20位'})
    app_svn_url = forms.CharField(max_length=200, error_messages={'required': 'svn路径不能为空', 'max_length': '最多20位'})
    app_svn_user = forms.CharField(max_length=20, error_messages={'required': 'svn用户不能为空', 'max_length': '最多20位'})
    app_svn_password = forms.CharField(max_length=20, error_messages={'required': 'svn密码不能为空', 'max_length': '最多20位'})
    execution_style = forms.CharField(max_length=20, error_messages={'required': '多主机执行顺序不能为空', 'max_length': '最多20位'})
    operation_content = forms.CharField(max_length=200, error_messages={'required': '没有选中的操作，请选择', 'max_length': '最多200位'})
    operation_arguments = forms.CharField(required=False, max_length=2000, error_messages={'max_length': '命令长度总和最多2000位'})
    app_backup_path = forms.CharField(required=False, max_length=200, error_messages={'max_length': '最多200位'})
    description = forms.CharField(required=False, max_length=200, error_messages={'max_length': '最多200位'})


# 发布系统 应用发布  更新应用表单验证 验证应用名称是否存在
def app_release_name_exist_validate(value):
    is_app_name_exist = AppRelease.objects.filter(app_name=value).exists()
    if not is_app_name_exist:
        raise ValidationError('应用名称不存在，请检查')


# 发布系统 应用发布  更新应用表单验证 主
class AppReleaseUpdateForm(forms.Form):
    app_name = forms.CharField(max_length=100, error_messages={'required': '应用名称不能为空', 'max_length': '最多100位'}, validators=[app_release_name_exist_validate])
    sys_type = forms.CharField(error_messages={'required': '系统类型不能为空'})
    minion_id = forms.CharField(validators=[app_release_minion_id_validate], error_messages={'required': 'Minion_ID不能为空'})
    app_path = forms.CharField(max_length=200, error_messages={'required': '应用目录不能为空', 'max_length': '最多200位'})
    app_path_owner = forms.CharField(max_length=20, error_messages={'required': '应用目录属主不能为空', 'max_length': '最多20位'})
    app_svn_url = forms.CharField(max_length=200, error_messages={'required': 'svn路径不能为空', 'max_length': '最多20位'})
    app_svn_user = forms.CharField(max_length=20, error_messages={'required': 'svn用户不能为空', 'max_length': '最多20位'})
    app_svn_password = forms.CharField(max_length=20, error_messages={'required': 'svn密码不能为空', 'max_length': '最多20位'})
    execution_style = forms.CharField(max_length=20, error_messages={'required': '多主机执行顺序不能为空', 'max_length': '最多20位'})
    operation_content = forms.CharField(max_length=200, error_messages={'required': '没有选中的操作，请选择', 'max_length': '最多200位'})
    operation_arguments = forms.CharField(required=False, max_length=2000, error_messages={'max_length': '命令长度总和最多2000位'})
    app_backup_path = forms.CharField(required=False, max_length=200, error_messages={'max_length': '最多200位'})
    description = forms.CharField(required=False, max_length=200, error_messages={'max_length': '最多200位'})


# 发布系统 应用组 表单验证 验证应用组名称是否重复
def app_group_name_validate(value):
    is_app_group_name_exist = AppGroup.objects.filter(app_group_name=value).exists()
    if is_app_group_name_exist:
        raise ValidationError('应用组名称已存在，请更换')


# 发布系统 应用组  新增应用组表单验证 主
class AppGroupAddForm(forms.Form):
    app_group_name = forms.CharField(max_length=50, error_messages={'required': '应用组名称不能为空', 'max_length': '最多50位'}, validators=[app_group_name_validate])
    description = forms.CharField(required=False, max_length=200, error_messages={'max_length': '最多200位'})


# 发布系统 应用组 表单验证 验证应用组名称是否重复
def app_group_name_exist_validate(value):
    is_app_group_name_exist = AppGroup.objects.filter(app_group_name=value).exists()
    if not is_app_group_name_exist:
        raise ValidationError('应用组名称不存在，请检查')


# 发布系统 应用组和应用授权 更新表单验证 验证应用名称是否存在
def app_group_members_validate(value):
    for app_name in value.split(','):
        is_app_name_exist = AppRelease.objects.filter(app_name=app_name).exists()
        if not is_app_name_exist:
            raise ValidationError('应用发布列表中没有应用名称：%s 的记录' % app_name)


# 发布系统 应用组  更新应用组表单添加成员验证 主
class AppGroupUpdateForm(forms.Form):
    app_group_name = forms.CharField(max_length=50, error_messages={'required': '应用组名称不能为空', 'max_length': '最多50位'}, validators=[app_group_name_exist_validate])
    app_group_members = forms.CharField(widget=forms.Textarea, validators=[app_group_members_validate], required=False)
    description = forms.CharField(required=False, max_length=200, error_messages={'max_length': '最多200位'})


# 发布系统 应用授权 表单验证 验证用户ID是否重复
def my_user_id_exist_validate(value):
    is_my_user_id_exist = AppAuth.objects.filter(my_user_id=value).exists()
    if is_my_user_id_exist:
        raise ValidationError('用户ID已存在，请检查')


# 发布系统 应用授权 表单验证 验证用户名称是否重复
def username_exist_validate(value):
    is_username_exist = AppAuth.objects.filter(username=value).exists()
    if is_username_exist:
        raise ValidationError('用户名称已存在，请检查')


# 发布系统 应用授权  创建用户 主
class AppAuthCreateForm(forms.Form):
    my_user_id = forms.IntegerField(error_messages={'required': '用户ID不能为空'}, validators=[my_user_id_exist_validate],)
    username = forms.CharField(max_length=50, error_messages={'required': '用户名称不能为空', 'max_length': '最多50位'}, validators=[username_exist_validate],)


# 发布系统 应用授权 更新表单验证 验证应用组名称是否存在
def app_group_validate(value):
    for app_group in value.split(','):
        is_app_group_exist = AppGroup.objects.filter(app_group_name=app_group).exists()
        if not is_app_group_exist:
            raise ValidationError('应用发布组列表中没有应用组名称：%s 的记录' % app_name)


# 发布系统 应用授权  更新应用授权表单添加权限验证 主
class AppAuthUpdateForm(forms.Form):
    my_user_id = forms.IntegerField(error_messages={'required': '用户ID不能为空'})
    username = forms.CharField(max_length=50, error_messages={'required': '用户名称不能为空', 'max_length': '最多50位'})
    app_perms = forms.CharField(widget=forms.Textarea, validators=[app_group_members_validate], required=False)
    app_group_perms = forms.CharField(widget=forms.Textarea, validators=[app_group_validate], required=False)
    description = forms.CharField(required=False, max_length=200, error_messages={'max_length': '最多200位'})


# 资源管理 主机列表 表单验证 验证服务器名称是否重复
def server_name_exist_validate(value):
    is_server_name_exist = ServerList.objects.filter(server_name=value).exists()
    if is_server_name_exist:
        raise ValidationError('服务器名称已存在，请检查')


# 资源管理 主机列表  新增主机表单验证 主
class ServerListAddForm(forms.Form):
    Server_Type = (
        ('0', '物理机'),
        ('1', '虚拟机')
    )
    server_name = forms.CharField(max_length=50, error_messages={'required': '服务器名称不能为空', 'max_length': '最多50位'}, validators=[server_name_exist_validate])
    server_type = forms.ChoiceField(required=False, choices=Server_Type, error_messages={'invalid_choice': '无效的服务器类型'})
    localhost = forms.CharField(required=False, max_length=50, error_messages={'max_length': '最多50位'})
    ip = forms.CharField(required=False, max_length=200, error_messages={'max_length': '最多50位'})
    system_issue = forms.CharField(required=False, max_length=50, error_messages={'max_length': '最多50位'})
    sn = forms.CharField(required=False, max_length=100, error_messages={'max_length': '最多50位'})
    cpu_num = forms.IntegerField(required=False, error_messages={'invalid': '无效的参数'})
    cpu_model = forms.CharField(required=False, max_length=100, error_messages={'max_length': '最多50位'})
    sys_type = forms.CharField(required=False, max_length=20, error_messages={'max_length': '最多50位'})
    kernel = forms.CharField(required=False, max_length=50, error_messages={'max_length': '最多50位'})
    product_name = forms.CharField(required=False, max_length=100, error_messages={'max_length': '最多50位'})
    ipv4_address = forms.CharField(required=False, max_length=900, error_messages={'max_length': '最多50位'})
    mac_address = forms.CharField(required=False, max_length=900, error_messages={'max_length': '最多50位'})
    mem_total = forms.IntegerField(required=False, error_messages={'invalid': '无效的参数'})
    mem_explain = forms.CharField(required=False, max_length=200, error_messages={'max_length': '最多50位'})
    disk_total = forms.IntegerField(required=False, error_messages={'invalid': '无效的参数'})
    disk_explain = forms.CharField(required=False, max_length=200, error_messages={'max_length': '最多50位'})
    minion_id = forms.CharField(required=False, max_length=20, error_messages={'max_length': '最多50位'})
    idc_name = forms.CharField(required=False, max_length=50, error_messages={'max_length': '最多50位'})
    idc_num = forms.CharField(required=False, max_length=50, error_messages={'max_length': '最多50位'})
    login_ip = forms.CharField(required=False, max_length=20, error_messages={'max_length': '最多50位'})
    login_port = forms.IntegerField(required=False, max_value=65535, min_value=1, error_messages={'invalid': '无效的参数','min_value': '从1开始', 'max_value': '最大65535'})
    login_user = forms.CharField(required=False, max_length=50, error_messages={'max_length': '最多50位'})
    login_password = forms.CharField(required=False, max_length=20, error_messages={'max_length': '最多50位'})
    description = forms.CharField(required=False, max_length=200, error_messages={'max_length': '最多50位'})