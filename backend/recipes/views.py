from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from .models import RecipeShortLink


def redirect_to_recipe(request, short_code):
    """Перенаправление по короткой ссылке на страницу рецепта"""
    short_link = get_object_or_404(RecipeShortLink, short_code=short_code)
    frontend_url = reverse(
        'frontend-recipe-detail', args=[short_link.recipe.pk]
    )
    full_url = request.build_absolute_uri(frontend_url)
    return redirect(full_url)
