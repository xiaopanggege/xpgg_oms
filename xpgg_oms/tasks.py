# Create your tasks here
from __future__ import absolute_import, unicode_literals
from celery import shared_task, uuid, result


@shared_task(bind=True, options={"task_id": "666666"})
def add(self, x, y):
    print('我是加法测试，会输出到celery日志中')
    print(result.AsyncResult.task_id)
    print(self.request.id)
    print('测试看能不能配置task_id')
    return x + y


# @periodic_task(options={"task_id": "my_periodic_task"})
def mul(x, y):
    return x * y


@shared_task(bind=True, task_id='555_'+uuid())
def xsum(numbers):
    return sum(numbers)
