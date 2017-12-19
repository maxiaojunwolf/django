from django.db import models
from django.contrib.auth.models import AbstractUser
from utils.models import BaseModel
from django.conf import settings
from goods.models import GoodsSKU
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

class User(AbstractUser, BaseModel):
    """用户"""
    class Meta:
        db_table = "df_users"

    def generate_active_token(self):
        """生成激活令牌由于每个用户注册时都需要调用此方法所以写到类里"""
        # (参数一：混淆字符，django内部提供，参数二：过期时间/秒)
        # 共分三步 ：
        # 1. 生成序列化器直接调用Serializer（）
        serializer = Serializer(settings.SECRET_KEY,3600)
        # 2.生成加密后的user_id,token传入字典使用dumps,返byte格式
        token = serializer.dumps({'user_id':self.id})
        # 3.返回解码后的token :默认utf8可以不填
        return token.decode()

class Address(BaseModel):
    """地址"""
    user = models.ForeignKey(User, verbose_name="所属用户")
    receiver_name = models.CharField(max_length=20, verbose_name="收件人")
    receiver_mobile = models.CharField(max_length=11, verbose_name="联系电话")
    detail_addr = models.CharField(max_length=256, verbose_name="详细地址")
    zip_code = models.CharField(max_length=6, verbose_name="邮政编码")

    class Meta:
        db_table = "df_address"