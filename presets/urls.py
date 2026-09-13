from django.urls import path

from . import views

app_name = 'presets'

urlpatterns = [
    path('', views.preset_list, name='list'),
    path('new/', views.create, name='create'),
    path('<int:pk>/', views.workspace, name='workspace'),
    path('<int:pk>/save/', views.save, name='save'),
    path('<int:pk>/clone/', views.clone, name='clone'),
    path('<int:pk>/delete/', views.delete, name='delete'),
]
