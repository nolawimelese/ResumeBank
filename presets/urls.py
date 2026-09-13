from django.urls import path

from . import views

app_name = 'presets'

urlpatterns = [
    path('', views.index, name='index'),
]
