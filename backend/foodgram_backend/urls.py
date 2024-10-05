from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from recipes.views import dummy_for_frontend_path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),
    path('api/', include('api.urls')),
    path('s/', include('recipes.urls')),
    path('recipes/<int:pk>/',
         dummy_for_frontend_path, name='frontend-recipe-detail'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
