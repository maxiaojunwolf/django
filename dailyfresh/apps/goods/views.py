from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.generic import View
from django_redis import get_redis_connection

from goods.models import GoodsCategory,Goods,GoodsSKU,IndexGoodsBanner, IndexPromotionBanner, IndexCategoryGoodsBanner

from orders.models import OrderGoods

from utils.models import BaseCartView


class IndexView(BaseCartView):
    '''查询主页信息，并填充到模板里'''
    def get(self,request):
        # 查询当前用户
        # request.user
        # 先判断是否有缓存，如果有直接返回缓存,如果没有则查询数据
        context = cache.get('index_page_data')
        if context is None:
            # 查询商品类别
            categorys = GoodsCategory.objects.all()
            # 查询轮播图
            index_goods_banners = IndexGoodsBanner.objects.all().order_by('index')
            # 查询广告位
            promotion_banners = IndexPromotionBanner.objects.all().order_by('index')
            # 查询商品分类;根据分类列表遍历查询出每个类别的商品
            for category in categorys:
                category_banner_title = IndexCategoryGoodsBanner.objects.filter(category=category,display_type=0).order_by('index')
                category_banner_show = IndexCategoryGoodsBanner.objects.filter(category=category,display_type=1).order_by('index')
                # 动态添加属性
                category.title_banners = category_banner_title
                category.image_banners = category_banner_show
            # 生成上下文信息
            context = {'categorys':categorys,
                       'index_goods_banners':index_goods_banners,
                       'promotion_banners':promotion_banners
                       }
            # 设置缓存内容和时间：
            cache.set('index_page_data',context,3600)
        # 补充购物车
        cart_num = self.getcart_num(request)
        # 购物车返回所有商品的总数和
        # 购物车显示必须先判断用户是否登陆，不登录则不需要查询
        context.update(cart_num=cart_num)
        # 返回数据
        return render(request,'index.html',context)

class Detailview(BaseCartView):
    '''商品详情视图'''
    # 商品详情页需要数据：购物车；商品列表；sku信息；评论；新品推荐
    def get(self,request,sku_id):
        # 首先必须知道谁要看谁的详情
        # 必须要传入商品id
        # 整个逻辑：先查询缓存，不存在则查询数据库，最后加上购物车信息
        context = cache.get('detail_%s'%sku_id)
        # 判断缓存有没有
        # context = None
        if context is None:
            # 查询数据库 ；凡是查询数据库都使用try捕捉异常
            try:
                sku = GoodsSKU.objects.get(id=sku_id)
            except GoodsSKU.DoesNotExist:
                # 商品不存在返回到主页
                return redirect(reversed('goods:index'))
            # 获取商品列表
            categorys = GoodsCategory.objects.all()
            # 从订单表中获取评论
            sku_orders = sku.ordergoods_set.all().order_by('-create_time')[:30]
            # 遍历评论列表
            if sku_orders:
                for sku_order in sku_orders:
                    # 查询创建时间
                    sku_order.ctime = sku_order.create_time.strftime('%Y-%m-%d %H:%M:%S')
                    # 查询评论用户名：多对一的关系直接点--找到订单-点-找到用户--点--找到用户名
                    sku_order.username = sku_order.order.user.username
            else:
                sku_order = []
            #获取最新推荐
            new_skus = GoodsSKU.objects.filter(category=sku.category).order_by('-create_time')[:2]

            # 获取其他规格的商品
            goods_skus = sku.goods.goodssku_set.exclude(id=sku_id)
            # 构造上下文
            context = {
                'categorys': categorys,
                'sku': sku,
                'orders': sku_orders,
                'new_skus': new_skus,
                'goods_skus': goods_skus,
            }
        # 保存缓存文件
            cache.set('detail_%s'%sku_id,context,3600)

        # 逻辑分析：当查看了某个商品的详情页之后，对应的应该修改浏览记录
        # 如果是登陆用户
        if request.user.is_authenticated():
            # 创建redis操作对象
            redis_coon = get_redis_connection('default')
            user_id = request.user.id
            # 删除该商品的原有记录
            redis_coon.lrem('history_%s'%user_id,0,sku_id)
            # 更新记录
            redis_coon.lpush('history_%s'%user_id,sku_id)
            # 最多保存5条记录
            redis_coon.ltrim('history_%s'%user_id,0,4)
        # 购物车数据
        cart_num = self.getcart_num(request)
        context.update({'cart_num':cart_num})

        return render(request,'detail.html',context)

class ListView(BaseCartView):
    '''展示商品列表'''
    # 逻辑分析：请求类型get 先看页面有什么--谁要看什么--都有什么要求
    def get(self,request,category_id,page):
        # 首先要知道需要显示哪一类的列表,所以必须传入参数
        # list/category_id/page_num/?sort=''
        # 接收参数---校验参数和要求--查询数据库--按要求排序
        sort = request.GET.get('sort','dedault') # 当没有参数时，给出默认参数
        # 查询类别是否存在
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return redirect(reverse('goods:index'))

        # 根据排序要求查询商品列表
        if sort == 'price':
            skus = GoodsSKU.objects.filter(category=category).order_by('price')
        # 注意默认销量排序都是从小到大的，但是根据常规一般显示是从大到小的所以要使用‘-’取反
        elif sort == 'hot':
            skus = GoodsSKU.objects.filter(category=category).order_by('-sales')
        # 为了避免不正常传参，使用else，处理其他情况都为默认排序
        else:
            skus = GoodsSKU.objects.filter(category=category)

        # 分页显示使用djan自带的Paginator
        # 获取分页参数
        page = int(page)
        # Paginator 参数（内容,每页多少条）
        try:
            paginator = Paginator(skus,2)
            page_skus = paginator.page(page)
        except EmptyPage:
            # 如果传入的页码不存在就默认返回第一页
            page_skus = paginator.page(1)
            page = 1
        # 获取总页数列表
        page_list = paginator.page_range
        # 补充新品推荐和购物车
        # 购物车信息
        cart_num = self.getcart_num(request)
        # 获取最新推荐
        new_skus = GoodsSKU.objects.filter(category=category).order_by('-create_time')[0:2]
        # 所有分类信息
        categorys = GoodsCategory.objects.all()
        # 构造上下文
        context = {
            'category':category,
            'categorys':categorys,
            'new_skus':new_skus,
            'page_skus':page_skus,
            'page_list':page_list,
            'sort':sort,
            'cart_num':cart_num,
        }
        return render(request,'list.html',context)