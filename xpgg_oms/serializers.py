from rest_framework import serializers
from .models import AppRelease


class AppReleaseListSerializer(serializers.ModelSerializer):
    class Meta:
        # 设置继承的数据库
        model = AppRelease
        # 设置显示的字段
        # fields = ('id', 'title', 'code', 'linenos', 'language', 'style')
        fields = "__all__"  # 取所有字段