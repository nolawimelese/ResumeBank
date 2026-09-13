from django.urls import path

from . import views

app_name = 'bank'

urlpatterns = [
    path('', views.index, name='index'),
    path('profile/', views.profile, name='profile'),
    path('education/new/', views.education_new, name='education_new'),
    path('education/<int:pk>/', views.education_edit, name='education_edit'),
    path('education/<int:pk>/delete/', views.education_delete, name='education_delete'),
    path('components/new/', views.component_new, name='component_new'),
    path('components/<int:pk>/', views.component_edit, name='component_edit'),
    path('components/<int:pk>/delete/', views.component_delete, name='component_delete'),
    path('skills/', views.skills, name='skills'),
]
