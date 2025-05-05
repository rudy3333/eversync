from django.urls import path
from . import views



urlpatterns = [
    path('', views.index, name='index'),
    path('logoutz/', views.logout_view, name='logoutz'),
    path('register/', views.register, name='register'),
    path('manage/', views.manage, name='manage'),
    path('change_username/', views.change_username, name="change_username"),
    path('change_password/', views.change_password, name="change_password")
]
