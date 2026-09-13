"""
URL configuration for ResumeBank project.

    /           bank      component manager (Profile, Education, Components, Skills)
    /presets/   presets   preset list and the workspace (structure form + live PDF preview)
    /compile/   compiler  preview / save-to-history endpoints used by the workspace, history page
    /admin/     django admin
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('bank.urls')),
    path('presets/', include('presets.urls')),
    path('compile/', include('compiler.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
