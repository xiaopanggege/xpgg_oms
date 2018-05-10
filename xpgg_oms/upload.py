# 新增py，作用是富文本编辑框的文件上传没有配置这个是有问题的，所以需要配置这个来实现富文本编辑框里的上传功能
# -*- coding: utf-8 -*-
from django.http import HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import os
import uuid
import json
import datetime


# 加这个装饰器就忽略了表单验证
@csrf_exempt
def upload_image(request, dir_name):
    # dir_name就是url中的(?P<dir_name>[^/]+)
    # kindeditor图片上传返回数据格式说明：
    # {"error": 1, "message": "出错信息"}
    # {"error": 0, "url": "图片地址"}
    result = {"error": 1, "message": "上传出错"}
    files = request.FILES.get("imgFile", None)  # imgFile是富文本上传框里本地上传按钮“浏览”的name在html按F12查看
    if files:
        result = image_upload(files, dir_name)
    return HttpResponse(json.dumps(result), content_type="application/json")


# 目录创建
def upload_generation_dir(dir_name):
    today = datetime.datetime.today()
    dir_name = dir_name + '/%d/%d/' % (today.year, today.month)
    if not os.path.exists(settings.MEDIA_ROOT + dir_name):
        os.makedirs(settings.MEDIA_ROOT + dir_name)
    return dir_name


# 图片上传
def image_upload(files, dir_name):
    # 允许上传文件类型
    allow_suffix = ['jpg', 'png', 'jpeg', 'gif', 'bmp']
    file_suffix = files.name.split(".")[-1]
    if file_suffix not in allow_suffix:
        return {"error": 1, "message": "图片格式不正确"}
    relative_path_file = upload_generation_dir(dir_name)
    path = os.path.join(settings.MEDIA_ROOT, relative_path_file)
    # 上面这个是图片保存位置和数据库ImageField字段的上级目录相同，静态文件尽量放一起 好处理
    if not os.path.exists(path):  # 如果目录不存在创建目录
        os.makedirs(path)
    file_name = str(uuid.uuid1())+"."+file_suffix
    path_file = os.path.join(path, file_name)
    file_url = settings.MEDIA_URL + relative_path_file + file_name
    open(path_file, 'wb').write(files.file.read())  # 保存图片
    return {"error": 0, "url": file_url}
