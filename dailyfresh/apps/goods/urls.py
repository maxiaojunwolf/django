from django.conf.urls import url
from goods import views

urlpatterns = [
    url(r'^index$', views.IndexView.as_view(), name='index'),
    url(r'^detail/(?P<sku_id>\d+)/$', views.Detailview.as_view(), name='detail'),
    url(r'^list/(\d+)/(\d+)/$', views.ListView.as_view(), name='list'),



]