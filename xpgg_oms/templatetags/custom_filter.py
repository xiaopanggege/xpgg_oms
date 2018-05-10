# 这个是自己新建的文件夹和py文件

# 自定义过滤器，这个使用起来会让代码实现的功能更加灵活高效，要记得遇到难点可以考虑使用
# 相应的还有自定义tag
# 在使用时不要忘了在模板文件头部写入{% load my_split %}
# 注意必须写在这个templatetags文件夹下，这个是django默认可以识别的

from django import template

import logging
# Create your views here.
logger = logging.getLogger('xpgg_oms.views')

# 首先创建一个全局register变量，它是用来注册你自定义标签和过滤器的！
register = template.Library()


# 这个name是在html调用的时候的名字比如{{xxx | percent1}}，name='aaa'那调用就是{{xxx | aaa}}
# 给流程管理的流程信息用的过滤器
@register.filter(name='my_split')
def my_split(value, arg):
    try:
        # arg表示在用这个自定义过滤器的时候要代入参数，{{ value|percent1:'aa' }}
        return value.split(arg)
    except Exception as e:
        logger.error('自定义my_split过滤器代入参数有误'+str(e))
        return value
# register.filter('percent1',percent1) #本来在最后顶格要加这个不过这段被上面的装饰器代替了


# 给流程管理的流程参数用的过滤器
@register.filter(name='my_eval')
def my_eval(value):
    try:
        # 虽然在模板中字典是{{ dict.items }}这么引用的，但是在后端必须是items()，发送到前端后自动会变成dict.items放心，不加()反而错
        return eval(value).items()
    except Exception as e:
        logger.error('自定义my_eval过滤器代入参数有误'+str(e))
        logger.error(value)
        return value

