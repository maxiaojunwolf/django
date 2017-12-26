import re

from django.contrib.auth import authenticate, login, logout
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.generic import View
# 定义类视图
from django_redis import get_redis_connection
from djcelery import db
from itsdangerous import  SignatureExpired
from pymysql import IntegrityError
from users.models import User

from users.models import Address

from goods.models import GoodsSKU
from celery_tasks.tasks import send_active_email
# 处理注册功能
from dailyfresh import settings
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

from utils.views import LoginRequiredMixin


class RegisterView(View):
    # 1. 返回注册页面get
    def get(self,request):
        return render(request, 'users/register.html')
    # 2.接收post参数
    def post(self,request):
        #获取用户填写数据
        # 获取注册请求参数
        print('laikee')
        user_name = request.POST.get('user_name')
        password = request.POST.get('pwd')
        cpassword = request.POST.get('cpwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        # 参数校验：缺少任意一个参数，就不要在继续执行
        if not all([user_name, password,cpassword, email]):
            return redirect(reverse('users:register'))
        # 判断邮箱
        if not re.match(r"^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$", email):
            return render(request, 'users/register.html', {'errmsg': '邮箱格式不正确'})
        # 判断是否勾选协;未勾选时返回none
        if allow != 'on':
            return render(request, 'users/register.html', {'errmsg': '没有勾选用户协议'})

        #保存数据到数据库
        try:
            # 隐私信息需要加密，可以直接使用django提供的用户认证系统完成,查看用户是否存在（因为username字段属性包含unique)
            user = User.objects.create_user(user_name, email, password)
        except IntegrityError:
            return render(request, 'users/register.html', {'errmsg': '用户已注册'})

        # 手动的将用户认证系统默认的激活状态is_active设置成False,默认是True
        user.is_active = False
        # 保存数据到数据库
        user.save()
        # 生成激活token
        token = user.generate_active_token()

        # celery发送激活邮件：异步完成，发送邮件不会阻塞结果的返回
        send_active_email.delay(email, user_name, token)

        # 返回结果：比如重定向到首页
        return redirect(reverse('goods:index'))
        # return HttpResponse('ok')
class ActiveView(View):
    '''邮件激活'''
    # 判断请求类型
    def get(self,request,token):
        # 处理请求
        # 通过原有的序列号生成器获取数据
        serializer = Serializer(settings.SECRET_KEY, 3600)
        # 判断是否过期

        # 转换数据
        try:
            result = serializer.loads(token)
            print(result)
        except SignatureExpired:
            return HttpResponse('激活链接过期')
        # # 取出id
        user_id = result.get('user_id')
        # 查询数据库对比
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return HttpResponse('用户不存在')
        # 是否激活
        if user.is_active == True:
            return HttpResponse('请不要重复激活')
        # 修改is_active
        user.is_active = True
        # 保存
        user.save()
        # 返回
        return redirect(reverse('goods:index'))
class LoginView(View):
    '''登陆'''
    # 请求get登陆界面
    def get(self,request):
        return render(request,'login.html')
    # 处理post提交的数据
    def post(self,request):
        # 获取数据用户名/密码
        user_name = request.POST.get('user_name')
        password = request.POST.get('pwd')
        remembered = request.POST.get('remembered')
        # 判断不能为空
        if not all([user_name,password]):
            return redirect(reverse('user:login'))
        # 查询数据库是否正确
        user = authenticate(username=user_name,password=password)
        if user is None:
            return render(request,'login.html',{'errmsg':'用户名或密码错误'})
        # 查询是否已经通过了验证
        if user.is_active is False:
            return render(request,'login.html',{'ermsg':'您尚未激活'})
        # 修改登陆状态(注意login的参数）
        login(request,user)
        # 登陆状态的记录,判断是否勾选记住登陆状态
        if remembered !='on':
            request.session.set_expiry(0)
        else:
            request.session.set_expiry(3600*24)
        context = {'user_name':user_name}
        next = request.GET.get('next')
        if next is None:
            # 返回主页
            return render(request,'index.html',context)
        else:
            return redirect(next)
        # return HttpResponse('ok')
# 退出登陆
class LogoutView(View):
    '''逻辑请求仅仅包含get,退出登陆返回一个页面'''
    def get(self,request):
        # 通过django自带模块完成退出登陆Logout,一个参数request
        logout(request)
        return redirect(reverse('goods:index'))
# 用户中心
class UserInfoView(LoginRequiredMixin,View):
    def get(self,request):

        return render(request,'user_center_info.html')
# 用户中心--地址管理展示
class AddressView(LoginRequiredMixin,View):
    '''1.返回页面数据 2.post编辑地址'''
    def get(self,request):
        # 获取用户名：requrest.user
        user = request.user
        # 查询地址信息，latest按照时间排序
        try:  # 查询要带try 防止出错
            address = user.address_set.latest('create_time')
        except Address.DoesNotExist:
            address = None
        # 创建redis链接对象
        redis_connection = get_redis_connection('default')
        # 查询redis数据库sku_id
        sku_ids = redis_connection.lrange('history_%s'%user.id,0,4)
        # 查询sku信息，要求保证顺序一致，所以使用list保存
        sku_list = []
        # 遍历查询sku
        for sku_id in sku_ids:
            sku = GoodsSKU.objects.filter(id=sku_id)
            sku_list.append(sku)
        # 返回地址对象
        print(sku_list)
        context = {'address': address,'sku_list':sku_list}
        return render(request,'user_center_site.html',context)
    def post(self,request):
        # 在多继承的类中完成登陆状态的判断
        # 获取用户名，得知到添加谁的地址
        user = request.user
        # 获取post数据
        recv_name = request.POST.get('recv_name')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        recv_mobile = request.POST.get('recv_mobile')
        # 数据校验all()
        if not all([recv_name,addr,zip_code,recv_mobile]):
            return redirect(reverse('users:address'))
        # 保存数据 create自带save
        Address.objects.create(
            user = user,
            receiver_name = recv_name,
            receiver_mobile = recv_mobile,
            detail_addr = addr,
            zip_code = zip_code

        )
        # 返回页面
        return redirect(reverse('users:address'))