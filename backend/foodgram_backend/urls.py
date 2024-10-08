from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),
    path('api/', include('api.urls')),
    path('s/', include('recipes.urls')),
    path('recipes/<int:pk>/',
         TemplateView.as_view(
             template_name='empty.html'), name='frontend-recipe-detail'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
