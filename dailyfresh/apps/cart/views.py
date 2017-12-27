import json

from django.http import HttpResponse, response
from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic import View
from django_redis import get_redis_connection

from goods.models import GoodsSKU

from utils.models import BaseCartView


class AddCartView(BaseCartView):
    '''处理详情页面添加购物车功能'''
    # 由于页面变化仅仅是购物车数量的变化所以采用ajax异步post请求
    def post(self,request):
        # 接收参数
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        # 校验参数
        # 是否为空
        if not all([sku_id,count]):
            return JsonResponse({'code':1,'message':'参数不能为空'})
        # 数量是否超限
        # 查询数据库是否存在该商品
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'code':2,'message':'商品不存在'})
        # 判断count为整数
        try:
            count = int(count)
        except Exception:
            return JsonResponse({'code':3,'message':'商品数量必须为整数'})
        # 查询数据库的库存
        if count > sku.stock:
            return JsonResponse({'code':4,'message':'库存不足'})
        # 判断是否登陆
        if request.user.is_authenticated():
            # 如果登陆则保存到redis里
            redis_conn = get_redis_connection('default')
            # 查询数据库
            user_id = request.user.id
            # try: # 查询是否存在原有记录
            redis_conut = redis_conn.hget('cart_%s' % user_id, sku_id)
            if not redis_conut:
                redis_conut = 0
            # 保存数据
            redis_conn.hset('cart_%s'%user_id,sku_id,count+int(redis_conut))
            # 查询购物车总数量
            cart_num = self.getcart_num(request)
            #返回json 数据
            return JsonResponse({'code':0,'message':'success','cart_num':cart_num})
        # 如果未登录
        else:
            # 获取cookie查询有没有记录
            cookie_dict = request.COOKIES.get('cart')
            # 转换成json字典格式
            if cookie_dict:
                cookie_dict = json.loads(cookie_dict)
                  # cart_dict = json.loads(cart_json)
            # 获取已经保存的数量
                cook_count = cookie_dict.get(sku_id,0)
            else:
                cook_count = 0
                cookie_dict = {}
            # 重写cookie
            cookie_dict[sku_id] = cook_count + int(count)
            # 查询所有商品数量
            cart_num = self.getcart_num(request) + int(count)
            # 转换成json -str类型
            cookie_dict = json.dumps(cookie_dict)
            # 生成response
            response = JsonResponse({'code':0,'message':'success','cart_num':cart_num})
            # 重置cookies
            response.set_cookie('cart',cookie_dict)
            return response

class CartInfoView(BaseCartView):
    '''显示购物车信息'''
    def get(self,request):
        # 需要知道显示的是谁的购物车，所以分为登陆和非登陆状态
        #　如果登陆则查询redis数据库，如果没有则获取浏览器ｃｏｏｋｉｅｓ数据再查询数据库
        if request.user.is_authenticated():
            # 如果登陆
            # 获取用户名
            user_id = request.user.id
            # 查询遍历redis数据库
            redis_conn = get_redis_connection('default')
            redis_cart = redis_conn.hgetall('cart_%s'%user_id)
            # 查询mysql数据库返回sku对象
            sku_list = []
            all_price = 0
            all_count = 0
            for key,val in redis_cart.items():
                try:
                    sku = GoodsSKU.objects.get(id=int(key.decode()))
                except GoodsSKU.DoesNotExist:
                    continue
                else:
                    sku_list.append(sku)
                    sku.count = int(val.decode())
                    sku.all_price = (sku.price)*(sku.count)
                    all_price += sku.all_price
                    all_count += sku.count
            # 生成上下文
            context = {
                'skus':sku_list,
                'sku_amount':all_price,
                'total_count':all_count,
            }
        else:
            # 如果未登录查询cookies数据
            cook_cart = request.COOKIES.get('cart')
            if cook_cart:
                # 获取cookies;转换数据
                cook_cart = json.loads(cook_cart)
                sku_list = []
                all_price = 0
                all_count = 0
                # 查询数据库
                for key, val in cook_cart.items():
                    try:
                        sku = GoodsSKU.objects.get(id=int(key))
                    except GoodsSKU.DoesNotExist:
                        continue
                    else:
                        sku_list.append(sku)
                        sku.count = int(val)
                        sku.all_price = (sku.price) * (sku.count)
                        all_price += sku.all_price
                        all_count += sku.count
                # 构造上下文
                context = {
                    'skus': sku_list,
                    'sku.amount': all_price,
                    'total_count': all_count,
                }
            else:
                context = {}
        return render(request,'cart.html',context)
        # return HttpResponse('ok')

class UpdateView(BaseCartView):
    '''购物车数量的修改'''
    # 使用ajax进行异步请求，局部刷新页面post
    def post(self,request):
        # 获取传递的参数
        sku_count = request.POST.get('count')
        sku_id = request.POST.get('sku_id')
        user_id = request.user.id
        old_num = request.POST.get('old_num')
        # 校验参数
        if not all([sku_count,sku_id,user_id]):
            return JsonResponse({'code': 2, 'message': '参数有误'})
        # 查询redis，是否超过库存，修改数据
        try:
            sku = GoodsSKU.objects.get(id=int(sku_id))
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'code': 2, 'message': '参数有误'})
        if sku:
            if int(sku_count) <= sku.stock:
                if request.user.is_authenticated():
                    # 用户登陆时
                    # 修改cookies数据
                    redis_conn = get_redis_connection('default')
                    redis_conn.hset('cart_%s' % user_id, sku_id, sku_count)
                else:
                    # 未登录时
                    # 重置cookies数据
                    cook_cart = request.COOKIES.get('cart')
                    cook_cart[sku_id] = int(sku_count)
                # 返回数据
                return JsonResponse({'code': 0, 'sku_count': int(sku_count)})
            else:
                return JsonResponse({'code':1,'message':'库存不足'})

        else:
            return JsonResponse({'code': 2, 'message': '商品已下架'})
        # 依然分登陆和未登录状态
class DeleteCartView(BaseCartView):
    '''删除购物车数据'''
    # ajax异步刷新,分为登录和未登录情况
    def post(self,request):
        # 获取要删除的sku_id
        sku_id = request.POST.get('sku_id')
        # 查询数据是否存在
        # 根据登陆状态删除redis或者cookies数据
        if sku_id:
            if request.user.is_authenticated():
                # 如果是登陆用户
                # 链接redis数据库删除记录
                user_id = request.user.id
                redis_conn = get_redis_connection('default')
                # 删除记录
                if redis_conn.hget('cart_%s'%user_id,sku_id):
                    redis_conn.hdel('cart_%s'%user_id,sku_id)
                    return JsonResponse({'code':0,'message':'删除成功'})
                else:
                    return JsonResponse({'code': 1, 'message': '商品不存在'})
            else:
                cookie_cart = request.COOKIES.get('cart')
                if cookie_cart:
                    cookie_cart = json.loads(cookie_cart)
                    try:
                        del cookie_cart[sku_id]
                    except:
                        pass
                    else:
                        cookie_cart = json.dumps(cookie_cart)
                        response = JsonResponse({'code': 0, 'message': '删除成功'})
                        response.set_cookie('cart',cookie_cart)
                        return response
                else:
                    return JsonResponse({'code': 1, 'message': '商品不存在'})
