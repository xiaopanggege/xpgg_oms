from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from xpgg_oms.models import *
import time
import logging
# Create your views here.
logger = logging.getLogger('xpgg_oms.views')


# 后面选择手动添加用户所以下面的信号就不用了

# 在创建新用户的时候同时给应用授权表新建用户
# @receiver(post_save, sender=MyUser, dispatch_uid="myuser_post_save")
# def create_app_auth(sender, instance, created, update_fields, **kwargs):
#     updated_values = {'my_user_id': instance.id, 'username': instance.username}
#     AppAuth.objects.update_or_create(my_user_id=instance.id, defaults=updated_values)


# 在操作saltkey表的保存时候同时对minion管理表做创建或更新操作
@receiver(post_save, sender=SaltKeyList, dispatch_uid="saltkey_list_post_save")
def create_minion_list(sender, instance, created, update_fields, **kwargs):
    if created and instance.certification_status == 'accepted':
        updated_values = {'minion_id': instance.minion_id, 'minion_status': '在线', 'update_time': time.strftime('%Y年%m月%d日 %X')}
        MinionList.objects.update_or_create(minion_id=instance.minion_id, defaults=updated_values)


# 在操作saltkey表的删除时候同时对minion管理表做删除操作
@receiver(post_delete, sender=SaltKeyList, dispatch_uid="saltkey_list_post_delete")
def delete_minion_list(sender, instance, **kwargs):
    if instance.certification_status == 'accepted':
        MinionList.objects.filter(minion_id=instance.minion_id).delete()


# 在操作AppRelease表的删除时候同时对AppAuth表做删除对应权限操作
@receiver(post_delete, sender=AppRelease, dispatch_uid="AppRelease_post_delete")
def delete_app_auth_apprelease(sender, instance, **kwargs):
    app_auth_obj = AppAuth.objects.filter(app_perms__regex=r'^%s$|^%s,|,%s$|,%s,' % (instance.app_name, instance.app_name, instance.app_name, instance.app_name))
    for obj in app_auth_obj:
        app_perms_list = obj.app_perms.split(',')
        app_perms_list.remove(instance.app_name)
        obj.app_perms = ','.join(app_perms_list)
        obj.save()


# 在操作AppGroup表的删除时候同时对AppAuth表做删除对应权限操作
@receiver(post_delete, sender=AppGroup, dispatch_uid="AppGroup_post_delete")
def delete_app_auth_appgroup(sender, instance, **kwargs):
    app_auth_obj = AppAuth.objects.filter(app_group_perms__regex=r'^%s$|^%s,|,%s$|,%s,' % (instance.app_group_name, instance.app_group_name, instance.app_group_name, instance.app_group_name))
    for obj in app_auth_obj:
        app_group_perms_list = obj.app_group_perms.split(',')
        app_group_perms_list.remove(instance.app_group_name)
        obj.app_group_perms = ','.join(app_group_perms_list)
        obj.save()