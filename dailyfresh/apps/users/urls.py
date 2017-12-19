from django.conf.urls import include, url

from apps.users import views

urlpatterns = [
    url(r'^register$',views.RegisterView.as_view(),name='register'),
    url(r'^active/(?P<token>.+)$',views.ActiveView.as_view(),name='active'),
    url(r'^login$',views.LoginView.as_view(),name='login'),
    url(r'^logout$',views.LogoutView.as_view(),name='logout'),
    url(r'^info$',views.UserInfoView.as_view(),name='info'),
    url(r'^address$',views.AddressView.as_view(),name='address'),

]
