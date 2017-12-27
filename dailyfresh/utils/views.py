'''创建多继承类装饰器实现登陆状态的判定'''
from django.contrib.auth.decorators import login_required
from functools import wraps

from django.db import transaction
from django.http import JsonResponse


class LoginRequiredMixin(object):
    '''使用login_required装饰器,间接装饰as_view()d的结果'''
    @classmethod
    def as_view(cls,**initkwargs):
        view = super().as_view(**initkwargs)
        return login_required(view)


# 自定义一个装饰器主要是为了解决未登录状态时，LoginRequiredMixin返回的重定向，无法和json交互
# 所以自定义一个当判断没有登陆时返回json类型数据
def login_required_json(view_func):
    # 恢复view_func的名字和文档
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        # 如果用户未登录，返回json数据
        if not request.user.is_authenticated():
            return JsonResponse({'code': 1, 'message': '用户未登录'})
        else:
            # 如果用户登陆，进入到view_func中
            return view_func(request, *args, **kwargs)

    return wrapper

# 定义一个和json交互的登陆验证类
class LoginRequiredJSONMixin(object):

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)# 调用另一个父类的View方法转换成函数视图，再使用装饰器装饰
        return login_required_json(view)
# 利用django自带的atomic装饰器,定义一个类，实现django数据库事物
class TransactionAtomicMixin(object):

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)# 调用另一个父类的View方法转换成函数视图，再使用装饰器装饰
        return transaction.atomic(view)