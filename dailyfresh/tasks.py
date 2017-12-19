import os
os.environ["DJANGO_SETTINGS_MODULE"] = "dailyfresh.settings"
# 放到Celery服务器上时添加的代码
import django
django.setup()
from celery import Celery
from django.conf import settings
from django.core.mail import send_mail
# 创建celery客户端(参数一：任务路径，参数二：broker;redis://密码@ip/数据库)
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
                  'http://127.0.0.1:8000/users/active/%s</a></p>' %(user_name, token, token)
    send_mail(subject, body, sender, receiver, html_message=html_body)