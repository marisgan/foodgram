from rest_framework.routers import DefaultRouter
from django.urls import include, path

from api.views import (
    IngredientViewSet, RecipeViewSet, TagViewSet, MemberViewSet
)


app_name = 'api'

router = DefaultRouter()
router.register('recipes', RecipeViewSet, basename='recipe')
router.register('ingredients', IngredientViewSet, basename='ingredient')
router.register('tags', TagViewSet, basename='tag')
router.register('users', MemberViewSet, basename='user')


urlpatterns = [
    path('auth/', include('djoser.urls.authtoken')),
    path('', include(router.urls)),
]
