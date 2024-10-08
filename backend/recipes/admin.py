from django.contrib import admin
from django.contrib.admin import RelatedOnlyFieldListFilter
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.db.models import Count, Prefetch
from django.urls import reverse
from django.utils.safestring import mark_safe

from .constants import LONG_COOKING, MEDIUM_COOKING, QUICK_COOKING
from .models import (
    FavoriteRecipe, Ingredient, Product, Recipe,
    RecipeShortLink, ShoppingRecipe, Subscription, Tag, User
)
from .mixins import RecipesCountMixin


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
    readonly_fields = ('avatar_preview', )
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('avatar', 'avatar_preview')}),
    )
    search_fields = ('email', 'first_name', 'last_name', 'username')
    list_display_links = ('username',)

    def get_queryset(self, request):
        users = super().get_queryset(request)
        users = users.annotate(
            recipes_count=Count('recipes', distinct=True),
            subscriptions_count=Count('subscriptions', distinct=True),
            subscribers_count=Count('subscribed_to', distinct=True)
        )
        return users

    @mark_safe
    @admin.display(description='Превью')
    def avatar_preview(self, user):
        return (
            f'<img src="{user.avatar.url}" '
            'style="width: auto; max-height: 200px; '
            'object-fit: contain;" alt="Image Preview"/>'
        )

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

    @mark_safe
    @admin.display(ordering='-subscriptions_count',
                   description='Подписок')
    def subscriptions_count(self, user):
        count = user.subscriptions_count
        if count:
            url = reverse(
                'admin:recipes_subscription_changelist'
            ) + f'?user__id__exact={user.id}'
            return f'<a href="{url}">{count}</a>'
        return count

    @mark_safe
    @admin.display(ordering='-subscribers_count',
                   description='Подписчиков')
    def subscribers_count(self, user):
        count = user.subscribers_count
        if count:
            url = reverse(
                'admin:recipes_subscription_changelist'
            ) + f'?author__id__exact={user.id}'
            return f'<a href="{url}">{count}</a>'
        return count

    @mark_safe
    @admin.display(description='Аватар')
    def avatar_tag(self, user):
        return (
            f'<img src="{user.avatar.url}" '
            'style="width: auto; max-height: 60px; '
            'object-fit: contain;"/>' if user.avatar else ''
        )


class ProductInline(admin.TabularInline):
    model = Product
    extra = 1


class CookingTimeFilter(admin.SimpleListFilter):
    title = 'Время готовки (мин)'
    parameter_name = 'cooking_time'
    COOKING_TIME_FILTERS = {
        f'До {MEDIUM_COOKING[0]}': QUICK_COOKING,
        f'{MEDIUM_COOKING[0]} - {MEDIUM_COOKING[1]}': MEDIUM_COOKING,
        f'Дольше {MEDIUM_COOKING[1]}': LONG_COOKING
    }

    @staticmethod
    def filter_recipes(recipes, range_values):
        return recipes.filter(cooking_time__range=range_values)

    def lookups(self, request, model_admin):
        recipes = model_admin.get_queryset(request)
        lookups = []
        for key, range_values in self.COOKING_TIME_FILTERS.items():
            count = self.filter_recipes(recipes, range_values).count()
            lookups.append((key, f'{key} ({count})'))
        return lookups

    def queryset(self, request, queryset):
        filter_value = self.COOKING_TIME_FILTERS.get(self.value())
        if filter_value:
            return self.filter_recipes(queryset, filter_value)
        return queryset


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'image_tag', 'author', 'pub_date_short',
        'cooking_time', 'tags_pile', 'products_pile',
        'favorites_count', 'shopping_count'
    )
    readonly_fields = ('image_preview', )
    fieldsets = (
        (None, {
            'fields': (
                'name', 'author', 'pub_date',
                'cooking_time', 'image', 'image_preview', 'text',
            )
        }),
    )
    search_fields = ('name', 'author',)
    list_filter = (
        CookingTimeFilter,
        ('tags', RelatedOnlyFieldListFilter),
        ('author', RelatedOnlyFieldListFilter),
        ('ingredients', RelatedOnlyFieldListFilter),
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
            favorites_count=Count('favoriterecipes', distinct=True),
            shopping_count=Count('shoppingrecipes', distinct=True)
        )
        return recipes

    @admin.display(description='Дата')
    def pub_date_short(self, obj):
        return obj.pub_date.strftime('%d.%m.%y')

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
    @admin.display(description='Фотография')
    def image_tag(self, recipe):
        return (
            f'<img src="{recipe.image.url}" '
            'style="width: auto; max-height: 60px; '
            'object-fit: contain;"/>'
        )

    @mark_safe
    @admin.display(description='Превью')
    def image_preview(self, recipe):
        return (
            f'<img src="{recipe.image.url}" '
            'style="width: auto; max-height: 300px; '
            'object-fit: contain;" alt="Image Preview"/>'
        )

    @mark_safe
    @admin.display(description='В избранном у')
    def favorites_count(self, recipe):
        count = recipe.favorites_count
        if count:
            url = reverse(
                'admin:recipes_favoriterecipe_changelist'
            ) + f'?recipe__id__exact={recipe.id}'
            return f'<a href="{url}">{count}</a>'
        return count

    @mark_safe
    @admin.display(description='В списке покупок у')
    def shopping_count(self, recipe):
        count = recipe.shopping_count
        if count:
            url = reverse(
                'admin:recipes_shoppingrecipe_changelist'
            ) + f'?recipe__id__exact={recipe.id}'
            return f'<a href="{url}">{count}</a>'
        return count


@admin.register(Tag)
class TagAdmin(RecipesCountMixin, admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'recipes_count')
    list_display_links = ('id',)
    list_filter = (RecipesCountFilter, )
    annotate_field = 'recipes'
    table_name = 'recipe'
    related_field = 'tags'


@admin.register(Ingredient)
class IngredientAdmin(RecipesCountMixin, admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit', 'recipes_count')
    search_fields = ('name',)
    list_filter = (RecipesCountFilter, 'measurement_unit')
    list_display_links = ('id',)
    annotate_field = 'products__recipe'
    table_name = 'recipe'
    related_field = 'ingredients'


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'author')
    search_fields = ('user__username', 'author__username')
    list_display_links = ('id',)
    fields = ('user', 'author')
    list_filter = (
        ('user', RelatedOnlyFieldListFilter),
        ('author', RelatedOnlyFieldListFilter),
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipe', 'ingredient', 'amount')
    search_fields = ('recipe', 'ingredient')
    list_display_links = ('id',)
    list_filter = (
        'recipe',
        ('ingredient', RelatedOnlyFieldListFilter),
    )


class MemberRecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe',)
    search_fields = ('user', 'recipe')
    list_display_links = ('id',)
    list_filter = (
        ('user', RelatedOnlyFieldListFilter),
        ('recipe', RelatedOnlyFieldListFilter),
    )


@admin.register(ShoppingRecipe)
class ShoppingRecipeAdmin(MemberRecipeAdmin):
    pass


@admin.register(FavoriteRecipe)
class FavoriteRecipeAdmin(MemberRecipeAdmin):
    pass


@admin.register(RecipeShortLink)
class RecipeShortLinkAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipe', 'short_code',)
    search_fields = ('recipe',)
    list_display_links = ('id',)
