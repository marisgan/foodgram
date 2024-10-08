import random
import string
from datetime import datetime

from recipes.models import RecipeShortLink


def render_shopping_list(products, recipes):
    today = datetime.now().strftime('%d-%m-%Y')
    products_info = [
        f"{i}. {product['ingredient__name'].capitalize()} "
        f"({product['ingredient__measurement_unit']}) — "
        f"{product['total_amount']}"
        for i, product in enumerate(products, start=1)
    ]
    recipes_names = [recipe.name for recipe in recipes]

    return '\n'.join([
        f'Список покупок на дату: {today}',
        'Продукты:',
        *products_info,
        'Для приготовления следующих рецептов:',
        *recipes_names,
    ])


def generate_unique_short_code():
    while True:
        short_code = ''.join(
            random.choices(string.ascii_letters + string.digits, k=6)
        )
        if not RecipeShortLink.objects.filter(short_code=short_code).exists():
            return short_code
