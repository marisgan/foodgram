from django.http import HttpResponseRedirect
from hashids import Hashids

from .constants import FRONTEND_RECIPES_URL


hashids = Hashids(min_length=6, salt='my_salt')


def redirect_to_recipe(request, short_code):
    """Перенаправление по короткой ссылке на страницу рецепта"""
    recipe_id = hashids.decode(short_code)[0]
    frontend_url = request.build_absolute_uri(
        f'{FRONTEND_RECIPES_URL}{recipe_id}/'
    )
    return HttpResponseRedirect(frontend_url)
