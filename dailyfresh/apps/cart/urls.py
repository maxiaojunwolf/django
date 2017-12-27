from django.conf.urls import url
from cart.views import CartInfoView,UpdateView,AddCartView,DeleteCartView

urlpatterns = [
    url(r'^add$',AddCartView.as_view(),name='add'),
    url(r'^$',CartInfoView.as_view(),name='info'),
    url(r'^update$',UpdateView.as_view(),name='update'),
    url(r'^delete$',DeleteCartView.as_view(),name='delete'),
]