from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import View

from goods.models import GoodsCategory,Goods,GoodsSKU,IndexGoodsBanner, IndexPromotionBanner, \
    IndexCategoryGoodsBanner


class IndexView(View):
    '''查询主页信息，并填充到模板里'''
    def get(self,request):
        # 查询当前用户
        # request.user
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
        context = {'categorys':categorys,'index_goods_banners':index_goods_banners,'promotion_banners':promotion_banners
                   }
        # 返回数据
        return render(request,'index.html',context)