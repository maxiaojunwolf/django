import json

from django.db import models
from django.views.generic import View
from django_redis import get_redis_connection


class BaseModel(models.Model):
    """为模型类补充字段"""
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        abstract = True  # 说明是抽象模型类,不会迁移生成数据表
class BaseCartView(View):
    '''定义一个购物车数量显示的基类继承自View'''
    def getcart_num(self,request):
        # 如果登陆则从redis数据库查询数据
        if request.user.is_authenticated():
            redis_conn = get_redis_connection('default')
            user_id = request.user.id
            cart_num = 0
            cart = redis_conn.hvals('cart_%s' % user_id)
            for val in cart:
                cart_num += int(val)
            return cart_num
        else:
            # 如果未登录则从cookies查询
            # 获取cookies
            cookie_dict = request.COOKIES.get('cart')
            # 判断是否为空
            if cookie_dict:
                # 数据转换成json字典
                cookie_dict = json.loads(cookie_dict)
                cart_num = sum(cookie_dict.values())
            else:
                cart_num = 0
            return cart_num