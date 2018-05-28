from django.db import models
from django.contrib.auth.models import AbstractUser, AbstractBaseUser
# Create your models here.


# 继承admin的user表，不在这方面花太多精力自己做用户管理
class MyUser(AbstractUser):
    avatar = models.ImageField(upload_to='avatar/%Y/%m', max_length=200, blank=True, null=True, verbose_name='用户头像')

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = verbose_name
        ordering = ['id']

    def __str__(self):
        return self.username


# minion客户端信息表
class MinionList(models.Model):
    minion_id = models.CharField(max_length=20, verbose_name='MinionID', primary_key=True)
    ip = models.CharField(max_length=200, verbose_name='IP地址', blank=True, null=True)
    minion_version = models.CharField(max_length=20, verbose_name='Minion版本', blank=True, null=True)
    system_issue = models.CharField(max_length=200, verbose_name='系统版本', blank=True, null=True)
    sn = models.CharField(max_length=200, verbose_name='SN', blank=True, null=True)
    cpu_num = models.IntegerField(verbose_name='CPU核数', blank=True, null=True)
    cpu_model = models.CharField(max_length=200, verbose_name='CPU型号', blank=True, null=True)
    sys = models.CharField(max_length=200, verbose_name='系统类型', blank=True, null=True)
    kernel = models.CharField(max_length=200, verbose_name='内核', blank=True, null=True)
    product_name = models.CharField(max_length=200, verbose_name='品牌名称', blank=True, null=True)
    ipv4_address = models.CharField(max_length=900, verbose_name='ipv4地址', blank=True, null=True)
    mac_address = models.CharField(max_length=900, verbose_name='mac地址', blank=True, null=True)
    localhost = models.CharField(max_length=200, verbose_name='主机名', blank=True, null=True)
    mem_total = models.IntegerField(verbose_name='内存大小', blank=True, null=True)
    create_date = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.CharField(max_length=50, verbose_name='最近一次更新时间', blank=True, null=True)
    minion_status = models.CharField(max_length=50, verbose_name='Minion状态', blank=True, null=True)
    description = models.CharField(max_length=200, verbose_name='描述备注', blank=True, null=True)

    class Meta:
        verbose_name = 'Minion列表'
        verbose_name_plural = verbose_name
        ordering = ['minion_id']

    def __str__(self):
        return self.minion_id


# nginx信息表
class NginxManage(models.Model):
    ip = models.CharField(max_length=20, verbose_name='IP地址', unique=True)
    vip = models.CharField(max_length=20, verbose_name='VIP地址', blank=True, null=True)
    path = models.CharField(max_length=200, verbose_name='nginx目录')
    conf_path = models.CharField(max_length=200, verbose_name='nginx.conf目录')
    vhost_path = models.CharField(max_length=200, verbose_name='vhost目录', blank=True, null=True)
    logs_path = models.CharField(max_length=200, verbose_name='logs目录', blank=True, null=True)
    create_date = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.CharField(max_length=50, verbose_name='最近一次更新时间', blank=True, null=True)
    nginx_status = models.CharField(max_length=50, verbose_name='nginx状态', blank=True, null=True)
    minion_id = models.CharField(max_length=200, verbose_name='minion_id', blank=True, null=True)
    description = models.CharField(max_length=200, verbose_name='描述备注', blank=True, null=True)

    class Meta:
        verbose_name = 'nginx管理'
        verbose_name_plural = verbose_name
        ordering = ['id']

    def __str__(self):
        return self.ip


# salt-key信息表
class SaltKeyList(models.Model):
    minion_id = models.CharField(max_length=20, verbose_name='MinionID')
    certification_status = models.CharField(max_length=20, verbose_name='认证状态')
    update_time = models.CharField(max_length=50, verbose_name='最近一次更新时间', blank=True, null=True)

    class Meta:
        verbose_name = 'Salt-key信息表'
        verbose_name_plural = verbose_name
        ordering = ['id']

    def __str__(self):
        return self.id


# 应用发布系统 应用信息表
class AppRelease(models.Model):
    app_name = models.CharField(max_length=100, verbose_name='应用名称', primary_key=True)
    sys_type = models.CharField(max_length=20, verbose_name='系统类型', blank=True, null=True)
    minion_id = models.CharField(max_length=200, verbose_name='minion_id', blank=True, null=True)
    app_path = models.CharField(max_length=200, verbose_name='应用目录', blank=True, null=True)
    app_path_owner = models.CharField(max_length=20, verbose_name='应用目录属主', blank=True, null=True)
    app_svn_url = models.CharField(max_length=200, verbose_name='SVN路径', blank=True, null=True)
    app_svn_user = models.CharField(max_length=20, verbose_name='SVN账户', blank=True, null=True)
    app_svn_password = models.CharField(max_length=20, verbose_name='SVN密码', blank=True, null=True)
    app_svn_co_path = models.CharField(max_length=200, verbose_name='SVN检出目录', blank=True, null=True)
    app_svn_version = models.CharField(max_length=50, verbose_name='应用svn版本', blank=True, null=True)
    app_svn_version_success = models.CharField(max_length=50, verbose_name='最近一次发布成功svn版本', blank=True, null=True)
    execution_style = models.CharField(max_length=20, verbose_name='多主机执行顺序', blank=True, null=True)
    operation_content = models.CharField(max_length=200, verbose_name='操作内容', blank=True, null=True)
    operation_arguments = models.CharField(max_length=2000, verbose_name='操作参数', blank=True, null=True)
    app_backup_path = models.CharField(max_length=200, verbose_name='应用备份目录', blank=True, null=True)
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.CharField(max_length=50, verbose_name='最近一次发布时间', blank=True, null=True)
    description = models.CharField(max_length=200, verbose_name='描述备注', blank=True, null=True)

    class Meta:
        verbose_name = '应用发布信息表'
        verbose_name_plural = verbose_name
        ordering = ['create_time']

    def __str__(self):
        return self.app_name


# 应用发布系统 应用发布日志表
class AppReleaseLog(models.Model):
    app_name = models.CharField(max_length=100, verbose_name='应用发布名称', blank=True, null=True)
    log_content = models.TextField(verbose_name='日志内容', blank=True, null=True)
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    release_result = models.CharField(max_length=20, verbose_name='发布结果', blank=True, null=True)
    username = models.CharField(max_length=20, verbose_name='操作人', blank=True, null=True)

    class Meta:
        verbose_name = '应用发布日志表'
        verbose_name_plural = verbose_name
        ordering = ['id']

    def __str__(self):
        return str(self.id)


# 应用发布系统 应用发布组信息表
class AppGroup(models.Model):
    app_group_name = models.CharField(max_length=20, verbose_name='应用组名称', unique=True)
    app_group_members = models.TextField(verbose_name='应用组成员', blank=True, null=True)
    description = models.CharField(max_length=200, verbose_name='描述备注', blank=True, null=True)

    class Meta:
        verbose_name = '应用发布组信息表'
        verbose_name_plural = verbose_name
        ordering = ['id']

    def __str__(self):
        return str(self.id)


# 应用授权表
class AppAuth(models.Model):
    my_user_id = models.IntegerField(verbose_name='用户ID', unique=True)
    username = models.CharField(max_length=50, verbose_name='用户名称', unique=True)
    app_perms = models.TextField(verbose_name='应用权限', blank=True, null=True)
    app_group_perms = models.TextField(verbose_name='应用组权限', blank=True, null=True)
    update_time = models.CharField(max_length=50, verbose_name='最近更新时间', blank=True, null=True)
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    description = models.CharField(max_length=200, verbose_name='描述备注', blank=True, null=True)

    class Meta:
        verbose_name = '应用授权表'
        verbose_name_plural = verbose_name
        ordering = ['username']

    def __str__(self):
        return str(self.username)
    

# salt命令集信息表
class SaltCmdInfo(models.Model):
    salt_cmd = models.CharField(max_length=100, verbose_name='命令')
    salt_cmd_type = models.CharField(max_length=20, verbose_name='类型', blank=True, null=True)
    salt_cmd_module = models.CharField(max_length=200, verbose_name='模块', blank=True, null=True)
    salt_cmd_source = models.CharField(max_length=200, verbose_name='命令来源', blank=True, null=True)
    salt_cmd_doc = models.TextField(verbose_name='命令帮助信息', blank=True, null=True)
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.CharField(max_length=50, verbose_name='最近一次采集时间', blank=True, null=True)
    description = models.TextField(verbose_name='描述备注', blank=True, null=True)

    class Meta:
        # 复合主键其实就是联合唯一索引,因为必须2个判断唯一，另外这样会自动生成ID主键
        unique_together = ("salt_cmd", "salt_cmd_type")
        verbose_name = 'salt命令集表'
        verbose_name_plural = verbose_name
        ordering = ['salt_cmd_type', 'salt_cmd']

    def __str__(self):
        return self.salt_cmd


# 主机资源表 精力有限，这块本来是要设置非常多个表单的，以后如果有时间专门做CMDB的话，再来重构
class ServerList(models.Model):
    Server_Type = (
        (0, '物理机'),
        (1, '虚拟机')
    )

    server_name = models.CharField(max_length=50, verbose_name='服务器名称', unique=True)
    server_type = models.CharField(choices=Server_Type, verbose_name='服务器类型', blank=True, null=True)
    localhost = models.CharField(max_length=50, verbose_name='主机名', blank=True, null=True)
    ip = models.CharField(max_length=200, verbose_name='IP地址', blank=True, null=True)
    system_issue = models.CharField(max_length=200, verbose_name='系统版本', blank=True, null=True)
    sn = models.CharField(max_length=200, verbose_name='SN', blank=True, null=True)
    cpu_num = models.IntegerField(verbose_name='CPU核数', blank=True, null=True)
    cpu_model = models.CharField(max_length=200, verbose_name='CPU型号', blank=True, null=True)
    sys = models.CharField(max_length=200, verbose_name='系统类型', blank=True, null=True)
    kernel = models.CharField(max_length=200, verbose_name='内核', blank=True, null=True)
    product_name = models.CharField(max_length=200, verbose_name='品牌名称', blank=True, null=True)
    ipv4_address = models.CharField(max_length=900, verbose_name='ipv4列表', blank=True, null=True)
    mac_address = models.CharField(max_length=900, verbose_name='mac地址列表', blank=True, null=True)
    mem_total = models.IntegerField(verbose_name='内存大小', blank=True, null=True)
    create_date = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.CharField(max_length=50, verbose_name='最近一次更新时间', blank=True, null=True)
    minion_id = models.CharField(max_length=20, verbose_name='minion_id', blank=True, null=True)
    minion_version = models.CharField(max_length=20, verbose_name='Minion版本', blank=True, null=True)
    minion_status = models.CharField(max_length=50, verbose_name='Minion状态', blank=True, null=True)
    idc_name = models.CharField(max_length=50, verbose_name='机房名称', blank=True, null=True)
    idc_num = models.CharField(max_length=50, verbose_name='机柜号', blank=True, null=True)
    description = models.CharField(max_length=200, verbose_name='描述备注', blank=True, null=True)

    class Meta:
        verbose_name = '主机列表'
        verbose_name_plural = verbose_name
        ordering = ['id']

    def __str__(self):
        return self.id