from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import *

# 后面选择手动添加用户所以下面的信号就不用了

# 在创建新用户的时候同时给应用授权表新建用户
# @receiver(post_save, sender=MyUser, dispatch_uid="myuser_post_save")
# def create_app_auth(sender, instance, created, **kwargs):
#     updated_values = {'my_user_id': instance.id, 'username': instance.username}
#     AppAuth.objects.update_or_create(my_user_id=instance.id, defaults=updated_values)

