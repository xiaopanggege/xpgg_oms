"""xiaopgg_project URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include  # 下面的include方法要加这个才能用
from django.contrib import admin
from django.conf import settings
from django.views import static
from xpgg_oms.upload import upload_image

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r"^media/(?P<path>.*)$", static.serve, {"document_root": settings.MEDIA_ROOT, }),
    # 上面的django.views.static.server是django自带专门处理静态文件的,在admin的用户表中添加用户头像字段里定义了路径和这里匹配就能在点击的时候直接显示
    url(r'^', include('xpgg_oms.urls')),
]
