from rest_framework.routers import DefaultRouter
from django.urls import include, path
from djoser import views as djoser_views

from api.views import (
    IngredientViewSet, RecipeViewSet, TagViewSet, CustomUserViewSet
)


app_name = 'api'

router = DefaultRouter()
router.register('recipes', RecipeViewSet, basename='recipe')
router.register('ingredients', IngredientViewSet, basename='ingredient')
router.register('tags', TagViewSet, basename='tag')
router.register('users', CustomUserViewSet, basename='user')


urlpatterns = [
    path('auth/', include('djoser.urls.authtoken')),
    path('', include(router.urls)),
    path('', include('djoser.urls')),
]
