from django.conf.urls import url
from orders.views import PlaceOrderView,CommitOrderView,UserOrdersView,PayView,CheckPayView,CommentView
urlpatterns = [
    url(r'^place$',PlaceOrderView.as_view(),name='place'),
    url(r'^commit$',CommitOrderView.as_view(),name='commit'),
    url(r'^(?P<page>\d+)$',UserOrdersView.as_view(),name='userorder'),
    url(r'^pay$',PayView.as_view(),name='pay'),
    url(r'^check_pay$',CheckPayView.as_view(),name='check_pay'),
    url(r'^comment/(?P<order_id>\d+)$',CommentView.as_view(),name='comment'),
]