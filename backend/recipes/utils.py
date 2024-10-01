from datetime import datetime


def render_shopping_list(products, recipes_names):
    today = datetime.now().strftime('%d-%m-%Y')
    products_info = [
        f"{i}. {product['ingredient__name'].capitalize()} "
        f"({product['ingredient__measurement_unit']}) — "
        f"{product['total_amount']}"
        for i, product in enumerate(products, start=1)
    ]

    return '\n'.join([
        f'Список покупок на дату: {today}',
        'Продукты:',
        *products_info,
        'Для приготовления следующих рецептов:',
        *recipes_names,
    ])
