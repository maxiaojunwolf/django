'''创建多继承类装饰器实现登陆状态的判定'''
from django.contrib.auth.decorators import login_required

class LoginRequiredMixin(object):
    '''使用login_required装饰器,间接装饰as_view()d的结果'''
    @classmethod
    def as_view(cls,**initkwargs):
        view = super().as_view(**initkwargs)
        return login_required(view)

