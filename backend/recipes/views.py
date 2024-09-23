from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from .models import Recipe


def redirect_to_recipe(request, short_id):
    """Перенаправление по короткой ссылке на страницу рецепта"""

    recipe = get_object_or_404(Recipe, short_id=short_id)
    recipe_url = reverse('api:recipe-detail', args=[recipe.id])

    return redirect(recipe_url.replace("/api", ""))
