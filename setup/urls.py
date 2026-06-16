from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token
from django.conf import settings # <-- IMPORTANTE
from django.conf.urls.static import static # <-- IMPORTANTE

urlpatterns = [
    path('admin/', admin.site.site_path if hasattr(admin.site, 'site_path') else admin.site.urls),
    path('api/', include('estoque.urls')),
    path('api/token/', obtain_auth_token),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) # <-- Libera a pasta de fotos