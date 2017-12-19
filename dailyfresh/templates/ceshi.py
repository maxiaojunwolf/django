import re
#实现静态文件路径替换
filename = 'index.html'
with open(filename) as f:
    msg = f.read()
    ret = re.findall(r'"../../static/(.*)"',msg)
    result = msg
    for i in ret:
        result = re.sub(r'../../static/[^"]+',"{% static '"+i+"' %}",result,1,flags=re.I)
with open(filename,'w') as f:
    f.write(result)