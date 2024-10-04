from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.db.models import Count, Prefetch
from django.urls import reverse
from django.utils.safestring import mark_safe

from .constants import COOKING_TIME_FILTERS
from .models import (
    FavoriteRecipe, Ingredient, Product, Recipe,
    ShoppingRecipe, Subscription, Tag, User
)


admin.site.empty_value_display = 'Не задано'

admin.site.unregister(Group)


class HasRecordsFilter(admin.SimpleListFilter):
    title = ''
    parameter_name = ''

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Есть записи'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(**{f'{self.parameter_name}__gt': 0})
        return queryset


class RecipesCountFilter(HasRecordsFilter):
    title = 'Есть рецепты'
    parameter_name = 'recipes_count'


class SubscriptionsCountFilter(HasRecordsFilter):
    title = 'Есть подписки'
    parameter_name = 'subscriptions_count'


class SubscribersCountFilter(HasRecordsFilter):
    title = 'Есть подписчики'
    parameter_name = 'subscribers_count'


@admin.register(User)
class MemberAdmin(UserAdmin):
    list_display = (
        'username', 'email', 'first_name', 'last_name', 'avatar_tag',
        'recipes_count', 'subscriptions_count', 'subscribers_count'
    )
    list_filter = (
        'is_staff', RecipesCountFilter, SubscriptionsCountFilter,
        SubscribersCountFilter
    )
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('avatar',)}),
    )
    search_fields = ('email', 'first_name', 'last_name', 'username')
    list_display_links = ('username',)

    def get_queryset(self, request):
        users = super().get_queryset(request)
        users = users.annotate(
            recipes_count=Count('recipes'),
            subscriptions_count=Count('subscriptions'),
            subscribers_count=Count('subscribed_to')
        )
        return users

    @mark_safe
    @admin.display(ordering='-recipes_count',
                   description='Рецептов')
    def recipes_count(self, user):
        count = user.recipes_count
        if count:
            url = reverse(
                'admin:recipes_recipe_changelist'
            ) + f'?author__id__exact={user.id}'
            return f'<a href="{url}">{count}</a>'
        return count

    @admin.display(ordering='-subscriptions_count',
                   description='Подписок')
    def subscriptions_count(self, user):
        return user.subscriptions_count

    @admin.display(ordering='-subscribers_count',
                   description='Подписчиков')
    def subscribers_count(self, user):
        return user.subscribers_count

    @mark_safe
    @admin.display(description='Аватар')
    def avatar_tag(self, user):
        return (
            f'<img src="{user.avatar.url}" width="30" height="30"/>'
        ) if user.avatar else ''


class ProductInline(admin.TabularInline):
    model = Product
    extra = 1


class CookingTimeFilter(admin.SimpleListFilter):
    title = 'Время готовки (мин)'
    parameter_name = 'cooking_time'

    def lookups(self, request, model_admin):
        return [(
            key,
            f'{key} ({COOKING_TIME_FILTERS[key][0]} - '
            f'{COOKING_TIME_FILTERS[key][1]} мин)'
        ) for key in COOKING_TIME_FILTERS
        ]

    def queryset(self, request, queryset):
        filter_value = COOKING_TIME_FILTERS.get(self.value())
        if filter_value:
            return queryset.filter(
                cooking_time__gte=filter_value[0],
                cooking_time__lt=filter_value[1]
            )
        return queryset


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'cooking_time', 'image_tag', 'author', 'pub_date',
        'tags_pile', 'products_pile',
        'favorites_count', 'shopping_count'
    )
    search_fields = ('name', 'author',)
    list_filter = (
        ('author', admin.RelatedOnlyFieldListFilter),
        CookingTimeFilter, 'tags',
    )
    list_display_links = ('id',)
    inlines = (ProductInline,)

    def get_queryset(self, request):
        recipes = super().get_queryset(request)
        recipes = recipes.prefetch_related(
            'tags',
            Prefetch(
                'products',
                queryset=Product.objects.select_related('ingredient')
            )
        ).annotate(
            favorites_count=Count('favoriterecipes'),
            shopping_count=Count('shoppingrecipes')
        )
        return recipes

    @mark_safe
    @admin.display(description='Теги')
    def tags_pile(self, recipe):
        return '<br>'.join(tag.name for tag in recipe.tags.all())

    @mark_safe
    @admin.display(description='Продукты')
    def products_pile(self, recipe):
        product_list = [
            f'{product.ingredient.name}'
            f'({product.ingredient.measurement_unit}) - '
            f'{product.amount}'
            for product in recipe.products.all()
        ]
        return '<br>'.join(product_list)

    @mark_safe
    @admin.display(description='Изображение')
    def image_tag(self, recipe):
        return (
            f'<img src="{recipe.image.url}" width="100" height="100" />'
        )

    @admin.display(description='В избранном у')
    def favorites_count(self, recipe):
        return recipe.favorites_count

    @admin.display(description='В списке покупок у')
    def shopping_count(self, recipe):
        return recipe.shopping_count


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug',)
    list_display_links = ('id',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit')
    search_fields = ('name',)
    list_filter = ('measurement_unit', )
    list_display_links = ('id',)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'author')
    search_fields = ('user__username', 'author__username')
    list_display_links = ('id',)
    list_filter = ('user', 'author',)
    fields = ('user', 'author')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipe', 'ingredient', 'amount')
    search_fields = ('recipe', 'ingredient')
    list_display_links = ('id',)
    list_filter = ('recipe', 'ingredient',)


@admin.register(ShoppingRecipe)
class ShoppingRecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe',)
    search_fields = ('user', 'recipe')
    list_display_links = ('id',)
    list_filter = ('user', 'recipe',)


@admin.register(FavoriteRecipe)
class FavoriteRecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe',)
    search_fields = ('user', 'recipe')
    list_display_links = ('id',)
    list_filter = ('user', 'recipe',)
