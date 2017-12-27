import os,time

from alipay import AliPay
from django.core.paginator import Paginator, EmptyPage
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.generic import View
from django.core.cache import cache
from django_redis import get_redis_connection
from goods.models import GoodsSKU
from users.models import Address
from django.utils import timezone
from orders.models import OrderInfo,OrderGoods

from dailyfresh import settings
from utils.views import LoginRequiredMixin, LoginRequiredJSONMixin, TransactionAtomicMixin

class PlaceOrderView(LoginRequiredMixin,View):
    '''处理生成订单页面'''
    def post(self,request):
        '''进入订单页面的路径分为两条1.购物车2.详情页直接点击立即购买,'''
        # 首先必须登陆验证,没有登陆先登陆,注意订单页面是post请求，而next请求是get
        # 接收的参数包括sku_ids ;[count]
        # 需要返回的参数包括 [地址,商品信息，数量，小计，总计]
        sku_ids = request.POST.getlist('sku_ids')
        count =  request.POST.get('count')
        user_id = request.user.id
        # 获取传递的参数，根据count的值是否存在可以区分是从那个页面进入的
        # 准备容器
        sku_list = []
        all_count = 0
        all_price = 0
        # 校验参数是否为空
        if  sku_ids:
        # 查询数据库商品是否存在
            # 创建redis对象
            redis_conn = get_redis_connection('default')
            for sku_id in sku_ids:
                try:
                    sku = GoodsSKU.objects.get(id=sku_id)
                except GoodsSKU.DoesNotExist:
                    # 个=如果商品不存在
                    print(6)
                    return  redirect(reverse('goods:index'))
                else:
                    if not count:
                        # 如果是从购物车来的
                        # 查询redis商品数量
                        redis_count = redis_conn.hget('cart_%s'%user_id,sku_id)
                        if not redis_count: # 如果购物车里不存在
                            print(5)
                            return redirect(reverse('cart:info'))
                        # 查询库存# 查询redis数量是否超标
                        try:
                            redis_count = int(redis_count)
                        except Exception:
                            print(4)
                            return redirect(reverse('cart:info'))
                        if (sku.status==True) and (redis_count<sku.stock):
                            subtotal_price = redis_count*sku.price
                            # 将每个商品的数量和小计价格以属性方式添加
                            sku_list.append(sku)
                            sku.count = redis_count
                            sku.amount = subtotal_price
                            # 统计商品总数和总价格
                            all_count += redis_count
                            all_price += subtotal_price
                        else:
                            # 商品已下架或者库存不足
                            print(3)
                            return redirect(reverse('cart:info'))

                    else:
                        # 从立即购买过来
                        # 未登录用户查询数量是否超标,是否上架
                        try:
                            count = int(count)
                        except Exception:
                            print(1)
                            return redirect(reverse('cart:info',args=sku_id))
                        if (sku.status != True) or (count > sku.stock):
                            print(2)
                            return redirect(reverse('cart:info', args=sku_id))
                        # 将数据写入redis数据库，方便commit订单
                        redis_conn.hset('cart_%s'%user_id,sku_id,count)
                        subtotal_count = count
                        subtotal_price = count*sku.price
                        sku_list.append(sku)
                        sku.count = subtotal_count
                        sku.amoun = subtotal_price
                        # 统计商品总数和总价格
                        all_count = count
                        all_price = subtotal_price
            try:
               # 错误写法 address = Address.objects.filter(user=request.user).latest('create_time')
                address = request.user.address_set.latest('create_time')
            except Address.DoesNotExist:
                return redirect(reverse('users:address'))
            # 生成上下文填充页面
            # 获取邮费
            trans_cost = 10
            total_amount = trans_cost+all_price
            context = {
                'skus':sku_list,
                'total_count':all_count,
                'total_sku_amount':all_price,
                'address':address,
                'trans_cost':trans_cost,
                'total_amount':total_amount,
                'sku_ids':",".join(sku_ids),
            }
            return render(request,'place_order.html',context)
        else:

            return HttpResponse('参数有误')

class CommitOrderView(LoginRequiredJSONMixin,TransactionAtomicMixin,View):
    def post(self,request):
        # 获取数据包括地址,支付方式，sku_id
        # 所谓的建立订单就是把订单信息写入数据库订单表里
        # 必须是登陆状态
        # 接收数据
        address = request.POST.get('address_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')
        user_id = request.user.id
        # 校验数据
        if not all([pay_method,sku_ids,address]):
            return JsonResponse({'code':2,'message':'参数有误'})
        #查询地址信息
        try:
            address = Address.objects.get(id=address)
        except Address.DoesNotExist:
            return JsonResponse({'code': 3, 'message': '地址不存在'})
        # 判断支付方式
        if pay_method in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'code': 4, 'message': '支付方式不能为空'})
        # 遍历sku_id
        try:
            sku_ids = sku_ids.split(',')
        except Exception:
            return JsonResponse({'code': 2, 'message': '参数有误'})
        # 创建redis对象
        redis_conn = get_redis_connection('default')
        # 因为遍历每个商品的时候都要存入order,所以必须在for循环外边先生成订单
        order_id = timezone.now().strftime('%Y%m%d%H%M%S')+str(user_id)
        # 创建订单表
        # 此处开始操作数据库,在这里设置一个还原点
        save_point = transaction.savepoint()
        user = request.user
        try:
            try:
                order = OrderInfo.objects.create(
                    order_id=order_id,
                    user=user,
                    address=address,
                    total_amount=0,
                    trans_cost=10,
                    pay_method=pay_method,
                )
            except Exception as a:
                # 回滚
                transaction.savepoint_rollback(save_point)
            total_acount = 0
            total_amount = 0
            skus = []
            for sku_id in sku_ids:
                for i in range(3):
                    # 查询数据库
                    try:
                        sku = GoodsSKU.objects.get(id=sku_id)
                    except GoodsSKU.DoesNotExist:
                        return JsonResponse({'code': 5, 'message': '商品不存在'})
                    # 查询数量小于库存
                    redis_count = redis_conn.hget('cart_%s'%user_id,sku_id)
                    # 如果数量为空
                    if not redis_count:
                        return JsonResponse({'code': 5, 'message': '商品不存在'})
                    # 查询数量,计算价格
                    try:
                        redis_count = int(redis_count)
                    except Exception:
                        return JsonResponse({'code': 6, 'message': '商品数量有误'})
                    # 判断库存和是否上架
                    if (redis_count > sku.stock) or (sku.status != True):
                        return JsonResponse({'code': 7, 'message': '库存不足'})

                    subtotal_price = redis_count*sku.price
                        # 增加sku销量，减少库存
                    # 在修改销量和库存时，使用乐观锁验证库存是否改变，没有改变就提交
                    origin_stock = sku.stock # 查出原来的数据
                    origin_sales = sku.sales
                    new_stock = origin_stock -redis_count
                    new_sales = origin_sales + redis_count
                    # 验证并更新数据库，执行失败返回0
                    result = GoodsSKU.objects.filter(id=sku_id,stock=origin_stock,sales=origin_sales).update(stock=new_stock,sales=new_sales)
                    # 考虑实际情况中每个人并不是只有一次机会成功,每个人可以循环三次
                    if 0 == result and i<2:
                        continue  # 继续抢
                    elif 0 == result and i == 2:
                        # 回滚
                        transaction.savepoint_rollback(save_point)
                        return JsonResponse({'code':8,'message':'下单失败'})
                        # 存入订单数据表
                    OrderGoods.objects.create(
                        order=order,  # 需要先生成订单
                        sku=sku,
                        count=redis_count,
                        price=sku.price,
                    )
                    # 统计总数量和总价格
                    total_acount += redis_count
                    total_amount += subtotal_price
                    break
            # 补充order字段参数数量和总价
            order.total_count = total_acount
            order.total_amount = total_amount
            order.save()
        except Exception as ret:
            # 回滚
            transaction.savepoint_rollback(save_point)
            print(ret)
        # 没有异常就手动提交
        transaction.savepoint_commit(save_point)
        # 返回json数据执行状态
        # 生成订单后删除购物车
        redis_conn.hdel('cart_%s'%user_id,*sku_ids)
        return JsonResponse({'code':0,'message':'创建订单成功'})

class UserOrdersView(LoginRequiredMixin,View):
    '''展示个人中心的订单'''
    def get(self,request,page):
        # 直接查询数据库的订单信息
        # 查询用户订单表
        try:
            user = request.user
            try:
                orders = user.orderinfo_set.all().order_by('-create_time')
            except OrderInfo.DoesNotExist:
                return HttpResponse('Error')
            # 判断订单
            if not orders:
                return render(request,'user_center_order.html')
            # 如果不为空遍历订单表获取sku
            for order in orders:
                # 查询订单的sku
                order.status_name = OrderInfo.ORDER_STATUS[order.status]
                order.pay_method = OrderInfo.PAY_METHODS[order.pay_method]
                # 准备一个sku列表容器
                order.skus = []
                # 根据订单查询订单商品
                order_skus = order.ordergoods_set.all()
                # 遍历所有订单商品
                # if not order_skus:
                #     print('jajja')
                #     return render(request, 'user_center_order.html')
                # 根本是要获取商品的sku夹带付款信息
                for order_sku in order_skus:
                    sku = order_sku.sku
                    sku.count = order_sku.count
                    sku.amount = sku.price*sku.count
                    order.skus.append(sku)
            # 分页
            page = int(page)
            try:
                paginator = Paginator(orders,2)
                page_orders = paginator.page(page)
            except EmptyPage:
                # 如果传入的页数不存在就默认 给第一页
                page_orders = paginator.page(1)
                page = 1
            # 页数
            page_list = paginator.page_range
            context = {
                'orders':orders,
                'page':page,
                'page_list':page_list,
            }
        except Exception as r:
            context = {}
        return render(request,'user_center_order.html',context)

class PayView(LoginRequiredMixin,View):
    '''支付处理发送支付请求给支付宝'''
    def post(self,request):
        # 订单id
        order_id = request.POST.get('order_id')
        # 校验订单
        if not order_id:
            return JsonResponse({'code': 2, 'message': '订单id错误'})

        # 获取订单信息
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=request.user,
                                          status=OrderInfo.ORDER_STATUS_ENUM["UNPAID"],
                                          pay_method=OrderInfo.PAY_METHODS_ENUM["ALIPAY"])

        except OrderInfo.DoesNotExist:
            return JsonResponse({'code': 3, 'message': '订单错误'})

        # 创建用于支付宝支付的对象

        alipay = AliPay(
            appid=settings.ALIPAY_APPID,# 支付宝url
            app_notify_url=None,  # 默认回调url,因为需要公网ip所以我们采用主动循环询问的方式
            # 自己的私钥
            app_private_key_path=os.path.join(settings.BASE_DIR, 'apps/orders/app_private_key.pem'),
            # 支付宝的公钥
            alipay_public_key_path=os.path.join(settings.BASE_DIR, 'apps/orders/alipay_public_key.pem'),
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            # 生成密钥时的转码方式
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False 配合沙箱模式使用
        )
        # 电脑网站支付，需要跳转到https://openapi.alipay.com/gateway.do? + order_string
        try:
            order_string = alipay.api_alipay_trade_page_pay(
                out_trade_no=order_id,
                total_amount=str(order.total_amount),  # 将浮点数转成字符串
                subject='头条生鲜',
                return_url=None,
                notify_url=None  # 可选, 不填则使用默认notify url
            )
        except Exception as ret:
            print(ret)
        # 生成url:让用户进入支付宝页面的支付网址
        url = settings.ALIPAY_URL + '?' + order_string
        return JsonResponse({'code': 0, 'message': '支付成功', 'url': url})

class CheckPayView(LoginRequiredJSONMixin, View):
    """检查订单状态"""

    def get(self, request):
        # 获取订单id
        order_id = request.GET.get('order_id')
        # 校验订单
        if not order_id:
            return JsonResponse({'code': 2, 'message': '订单id错误'})

        # 获取订单信息
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=request.user,
                                          status=OrderInfo.ORDER_STATUS_ENUM["UNPAID"],
                                          pay_method=OrderInfo.PAY_METHODS_ENUM["ALIPAY"])
        except OrderInfo.DoesNotExist:
            return JsonResponse({'code': 3, 'message': '订单错误'})

        # 创建用于支付宝支付的对象
        alipay = AliPay(
            appid=settings.ALIPAY_APPID,
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(settings.BASE_DIR, 'apps/orders/app_private_key.pem'),
            alipay_public_key_path=os.path.join(settings.BASE_DIR, 'apps/orders/alipay_public_key.pem'),
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False 配合沙箱模式使用
        )

        while True:
            # 查询支付结果:返回字典
            response = alipay.api_alipay_trade_query(order_id)

            # 判断支付结果
            code = response.get('code') # 支付宝接口调用结果的标志
            trade_status = response.get('trade_status') # 用户支付状态
            if code == '10000' and trade_status == 'TRADE_SUCCESS':
                # 表示用户支付成功
                # 设置订单的支付状态为待评论
                order.status = OrderInfo.ORDER_STATUS_ENUM['UNCOMMENT']
                # 设置支付宝对应的订单编号
                order.trade_id = response.get('trade_no')
                order.save()

                 # 返回json，告诉前端结果
                return JsonResponse({'code': 0, 'message': '支付成功'})

            elif code == '40004' or (code == '10000' and trade_status == 'WAIT_BUYER_PAY'):
                # 表示支付宝的接口暂时调用失败，网络延迟，订单还未生成；or 等待订单的支付
                # 继续查询
                continue
            else:
                # 支付失败，返回支付失败的通知
                return JsonResponse({'code': 4, 'message': '支付失败'})

class CommentView(LoginRequiredMixin,View):
    '''评论模块'''
    # get请求发送评论页面，post请求接收提交数据，添加到订单评论字段里
    def get(self,request,order_id):
        # 接收数据需要知道是那个订单，需要订单id
        user = request.user
        print('comment')
        # 需要查询该订单是否存在，是否是待评价页面
        try:
            order = OrderInfo.objects.get(order_id=order_id,user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('orders:userorder'))
        # 遍历订单商品，获取评论内容，添加到数据表里
        order.status_name = OrderInfo.ORDER_STATUS[order.status]
        order.skus = []
        order_skus = order.ordergoods_set.all()
        # 遍历订单商品，封装属性
        for order_sku in order_skus:
            sku = order_sku.sku
            sku.count = order_sku.count
            sku.amount = sku.price*sku.count
            order.skus.append(sku)
        return render(request,'order_comment.html',{'order':order})
    def post(self,request,order_id):
        """处理评论内容"""
        user = request.user
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse("orders:info"))

        # 获取评论条数
        total_count = request.POST.get("total_count")
        total_count = int(total_count)

        for i in range(1, total_count + 1):
            sku_id = request.POST.get("sku_%d" % i)
            content = request.POST.get('content_%d' % i, '')
            try:
                order_goods = OrderGoods.objects.get(order=order, sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue

            order_goods.comment = content
            order_goods.save()

            # 清除商品详情缓存
            cache.delete("detail_%s" % sku_id)

        order.status = OrderInfo.ORDER_STATUS_ENUM["FINISHED"]
        order.save()

        return redirect(reverse("orders:userorder", kwargs={"page": 1}))

