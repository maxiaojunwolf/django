from django.contrib import admin
from django.core.cache import cache
from goods.models import GoodsCategory, Goods, GoodsSKU

from goods.models import IndexPromotionBanner, IndexCategoryGoodsBanner
from celery_tasks.tasks import generate_static_index_html
# 自定义一个类
class BaseAdmin(admin.ModelAdmin):
    '''设置管理类,当管理员上传资料素材时调用生成新的静态文件'''
    def save_model(self, request, obj, form, change):
        '''重写内部save方法'''
        obj.save()
        # 调用异步生成静态文件
        generate_static_index_html.delay()
        # 删除原有缓存
        print(cache.get('index_page_data'))
        cache.delete('index_page_data')
        print(cache.get('index_page_data'))

    def delete_model(self, request, obj):
        obj.delete()
        generate_static_index_html.delay()

        cache.delete('index_page_data')
class IndexPromotionBannerAdmin(BaseAdmin):
    pass
class GoodsCategoryAdmin(BaseAdmin):
    pass

class GoodsAdmin(BaseAdmin):
    pass

class GoodsSKUAdmin(BaseAdmin):
    pass

class IndexCategoryGoodsBannerAdmin(BaseAdmin):
    pass
admin.site.register(GoodsCategory,GoodsCategoryAdmin)
admin.site.register(Goods,GoodsAdmin)
admin.site.register(GoodsSKU,GoodsSKUAdmin)
admin.site.register(IndexPromotionBanner,IndexPromotionBannerAdmin)
admin.site.register(IndexCategoryGoodsBanner,IndexCategoryGoodsBannerAdmin)