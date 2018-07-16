from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from .models import *
import time


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