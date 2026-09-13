from django.urls import path

from . import views

app_name = 'compiler'

urlpatterns = [
    path('history/', views.history, name='history'),
    path('<int:preset_id>/', views.compile_preset, name='compile'),
    path('<int:preset_id>/preview/', views.preview, name='preview'),
]
