"""
URL configuration for KargoSmart project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('tableau_de_bord.urls')),
    path('utilisateurs/', include('utilisateurs.urls')),
    path('livraisons/', include('livraisons.urls')),
    path('clients/', include('clients.urls')),
    path('notifications/', include('notifications.urls')),
    path('messages/', include('conversations.urls')),
    path('api/', include('api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
