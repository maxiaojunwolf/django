from django.contrib import admin
from goods.models import GoodsCategory, Goods, GoodsSKU

# Register your models here.
admin.site.register(GoodsCategory)
admin.site.register(Goods)
admin.site.register(GoodsSKU)
