from django.contrib import admin
from django.db.models import Count


from .models import (
    Recipe, Tag, Ingredient, Product
)


admin.site.empty_value_display = 'Не задано'


class ProductInline(admin.TabularInline):
    model = Product
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'text', 'cooking_time', 'image', 'author',
        'favorites_count', 'shopping_count'
    )
    list_editable = ('name', 'cooking_time')
    exclude = ('short_id',)
    search_fields = ('name', 'author',)
    list_filter = ('tags',)
    list_display_links = ('id',)
    inlines = (ProductInline,)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            favorites_count=Count('favoriterecipes'),
            shopping_count=Count('shoppingrecipes')
        )
        return queryset

    def favorites_count(self, obj):
        return obj.favorites_count

    def shopping_count(self, obj):
        return obj.shopping_count


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug',)
    list_editable = ('name', 'slug',)
    list_display_links = ('id',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit')
    list_editable = ('name', 'measurement_unit',)
    search_fields = ('name',)
    list_display_links = ('id',)
