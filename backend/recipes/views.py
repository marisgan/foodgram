from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from rest_framework import status
from hashids import Hashids

from .models import Recipe


hashids = Hashids(min_length=6, salt=settings.HASHID_SALT)


def redirect_to_recipe(request, short_code):
    """Перенаправление по короткой ссылке на страницу рецепта"""
    recipe_id = hashids.decode(short_code)[0]
    recipe = get_object_or_404(Recipe, pk=recipe_id)
    frontend_url = reverse('frontend-recipe-detail', args=[recipe.pk])
    full_url = request.build_absolute_uri(frontend_url)
    return redirect(full_url)


def dummy_for_frontend_path(request, *args, **kwargs):
    """Для построения маршрута на фронтенд через reverse()"""
    return HttpResponse(status=status.HTTP_204_NO_CONTENT)
