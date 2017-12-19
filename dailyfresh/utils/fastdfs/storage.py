from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client

from dailyfresh import settings


class FastDFSStorage(Storage):
    '''自定义django存储系统的类'''
    def __init__(self,client_conf=None,server_ip=None):
        '''初始化参数解耦，不一定在当前文件下'''
        if client_conf is None:
            client_conf = settings.CLIENT_CONF
        self.client_conf = client_conf
        if server_ip is None:
            server_ip = settings.SERVER_IP
        self.server_ip = server_ip

    def _open(self,name,mode='rb'):
        '''读取文件'''
        pass

    def _save(self,name,content):
        '''存储文件：参数一文件名，参数二file对象'''
        # 创建fdfs客户端client
        client = Fdfs_client(self.client_conf)
        # client 获取文件内容
        file_data = content.read()
        # django 借助client向FastDFS服务器上传数据
        print(1,type(file_data))
        try:
            result = client.upload_by_buffer(file_data)
        except Exception as e:
            raise
        # 根据返回数据判断上传是否成功
        print(result)
        if result.get('Status') == 'Upload successed.':
            # 读取file_id
            file_id = result.get('Remote file_id')

            # 返回给django存储起来即可
            return file_id
        else:
            # 开发工具时，出现异常不要擅自处理，交给使用者处理
            raise Exception('上传文件到FastDFS失败')
    def exists(self, name):
        '''django 用来判断文件是否存在的'''
        # 由于django不存储图片，所以返回永远都是False
        return False
    def url(self, name):
        ''' 用于返回图片在服务器上我完整地址'''
        return self.server_ip +name
