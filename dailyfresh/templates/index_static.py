import re
#实现静态文件路径替换
filename = 'index.html'
with open(filename) as f:
    msg = f.read()
    # 替换静态文件,导入路径
    msg = re.sub(r'<head>','<head>\r\n'+"    {% load staticfiles %}",msg,1)
    msg = re.sub(r'"css/reset.css"','"'+"{% static 'css/reset.css' %}"+'"',msg)
    msg = re.sub(r'"css/main.css"','"'+"{% static 'css/main.css' %}"+'"',msg)
    # print(msg)
    #src = "js/jquery-1.12.4.min.js"
    # 替换静态文件
    msg = re.sub(r'"js/jquery-1.12.4.min.js"','"'+"{% static 'js/jquery-1.12.4.min.js' %}"+'"',msg)
    msg = re.sub(r'"js/jquery-ui.min.js"','"'+"{% static 'js/jquery-ui.min.js' %}"+'"',msg)
    msg = re.sub(r'"js/slide.js"','"'+"{% static 'js/slide.js' %}"+'"',msg)
    # 替换照片
    ret = re.findall(r'"(images/[^"]+)"',msg)
    print(ret)
    result = msg
    for i in ret:
        i = '"{% static '+"'"+i+"'"+'%}"'
        print(i)
        result = re.sub(r'"images/(.*)"',i,result,1,flags=re.I)

with open(filename,'w') as f:
    f.write(result)

