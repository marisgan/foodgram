from django_filters import rest_framework as filters

from recipes.models import Ingredient, Recipe


class OneZeroFilter(filters.BooleanFilter):
    def filter(self, qs, value):
        if value == '1':
            value = True
        elif value == '0':
            value = False
        return super().filter(qs, value)


class RecipeFilter(filters.FilterSet):
    author = filters.NumberFilter(field_name='author__id')
    tags = filters.AllValuesMultipleFilter(field_name='tags__slug')
    is_favorited = OneZeroFilter(field_name='is_favorited')
    is_in_shopping_cart = OneZeroFilter(field_name='is_in_shopping_cart')

    class Meta:
        model = Recipe
        fields = ('author', 'tags', 'is_favorited', 'is_in_shopping_cart')


class IngredientFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='istartswith')

    class Meta:
        model = Ingredient
        fields = ['name']
