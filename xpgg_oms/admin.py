from django.contrib import admin
# 下面两条是为了用户表单在admin管理中显示使用的
from django.utils.translation import ugettext, ugettext_lazy as _
from django.contrib.auth.admin import UserAdmin
from .models import *
# Register your models here.


# 重写UserAdmin，因为如果直接register我的Myuser,UserAdmin的话我给用户表新增的头像字段avatar不显示，所以其实下面就是重写让我自定义字段显示
class MyUserAdmin(UserAdmin):
    # 修改一下admin管理页面用户表显示的字段，默认显示什么姓、名我又不需要，奶奶的
    list_display = ('username', 'last_login', 'date_joined', 'is_staff')
    # 下面就是修改页面显示的字段，我就加了一个自定义信息栏里面显示头像字段，没办法我只加了一个头像字段哈
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (_('自定义信息'), {'fields': ('avatar',)}),
    )
    # 这个是用户新增的时候显示的字段，我也就加了一个头像嘎嘎
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'avatar', 'password1', 'password2'),
        }),
    )


# 一定要加UserAdmin，不然在创建用户修改用户的时候密码会变成明文，各种问题，挖槽！！草！
admin.site.register(MyUser, MyUserAdmin)
admin.site.register(MinionList)
admin.site.register(NginxManage)
admin.site.register(SaltKeyList)
admin.site.register(AppRelease)
admin.site.register(AppReleaseLog)
admin.site.register(AppGroup)
