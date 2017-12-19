import os
from celery import Celery
from django.conf import settings
from django.core.mail import send_mail
# 创建celery客户端(参数一：任务路径，参数二：broker;redis://密码@ip/数据库)
from django.template import loader

from goods.models import GoodsCategory, IndexGoodsBanner, IndexPromotionBanner, IndexCategoryGoodsBanner

app = Celery('celery_tasks.tasks',broker='redis://192.168.8.133/2')
@app.task
def send_active_email(to_email,user_name,token):
    # 发送邮件
    subject = '天天生鲜激活'
    body = "" # 文本邮件体
    sender = settings.EMAIL_FROM #发件人
    receiver = [to_email] # 接受人
    html_body = '<h1>尊敬的用户 %s, 感谢您注册天天生鲜！</h1>' \
                '<br/><p>请点击此链接激活您的帐号<a href="http://127.0.0.1:8000/users/active/%s">' \
                'http://127.0.0.1:8000/users/active/%s</a></p>' % (user_name, token, token)
    send_mail(subject, body, sender, receiver, html_message=html_body)

@app.task
def generate_static_index_html():
    '''celery异步生成静态页面'''
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
        category_banner_title = IndexCategoryGoodsBanner.objects.filter(category=category, display_type=0).order_by(
            'index')
        category_banner_show = IndexCategoryGoodsBanner.objects.filter(category=category, display_type=1).order_by(
            'index')
        # 动态添加属性
        category.title_banners = category_banner_title
        category.image_banners = category_banner_show
    # 生成上下文信息
    context = {'categorys': categorys, 'index_goods_banners': index_goods_banners,
               'promotion_banners': promotion_banners
               }
    # 查询购物车
    cart_num = 0
    # 使用render原始方法生成页面
    template = loader.get_template('static_index.html')
    html_data = template.render(context)
    # 保存到静态文件中,避免将来布置代码后路径改变
    file_path = os.path.join(settings.STATICFILES_DIRS[0],'index.html')
    with open(file_path,'w') as f:
        f.write(html_data)