from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from estoque.views import SupabaseAuthTokenView

urlpatterns = [
    path('admin/', admin.site.site_path if hasattr(admin.site, 'site_path') else admin.site.urls),
    path('api/', include('estoque.urls')),
    path('api/token/', SupabaseAuthTokenView.as_view(), name='supabase-auth-token'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)