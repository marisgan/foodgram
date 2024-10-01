from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.db.models import Count, Prefetch
from django.utils.html import format_html, mark_safe

from .constants import MEDIUM_COOKING, QUICK_COOKING
from .models import (
    Ingredient, Member, Recipe, Tag, Subscription, Product,
    ShoppingRecipe, FavoriteRecipe
)


admin.site.empty_value_display = 'Не задано'

admin.site.unregister(Group)


User = get_user_model()


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


@admin.register(Member)
class MemberAdmin(UserAdmin):
    list_display = (
        'username', 'email', 'first_name', 'last_name', 'avatar',
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
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            recipes_count=Count('recipes'),
            subscriptions_count=Count('subscriptions'),
            subscribers_count=Count('subscribers')
        )
        return queryset

    @admin.display(ordering='-recipes_count',
                   description='Число рецептов')
    def recipes_count(self, user):
        count = user.recipes_count
        if count:
            url = (
                f'/admin/recipes/recipe/?author__id__exact={user.id}'
            )
            return format_html('<a href="{}">{}</a>', url, count)
        return count

    @admin.display(ordering='-subscriptions_count',
                   description='Число подписок')
    def subscriptions_count(self, user):
        return user.subscriptions_count

    @admin.display(ordering='-subscribers_count',
                   description='Число подписчиков')
    def subscribers_count(self, user):
        return user.subscribers_count


class ProductInline(admin.TabularInline):
    model = Product
    extra = 1


class RecipeAuthorFilter(admin.SimpleListFilter):
    title = 'Автор'
    parameter_name = 'author'

    def lookups(self, request, model_admin):
        authors = User.objects.filter(recipes__isnull=False).distinct()
        return [(
            author.id, author.get_full_name() or author.username
        ) for author in authors]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(author_id=self.value())
        return queryset


class CookingTimeFilter(admin.SimpleListFilter):
    title = 'Время готовки'
    parameter_name = 'cooking_time'

    def lookups(self, request, model_admin):
        quick = Recipe.objects.filter(
            cooking_time__lt=QUICK_COOKING).count()
        medium = Recipe.objects.filter(
            cooking_time__gte=QUICK_COOKING,
            cooking_time__lte=MEDIUM_COOKING).count()
        long = Recipe.objects.filter(
            cooking_time__gt=MEDIUM_COOKING).count()

        return [
            ('quick', f'Быстрые - до {QUICK_COOKING} минут ({quick})'),
            ('medium',
             f'Средние - {QUICK_COOKING}-{MEDIUM_COOKING} минут ({medium})'),
            ('long', f'Долгие - более {MEDIUM_COOKING} минут ({long})')
        ]

    def queryset(self, request, queryset):
        if self.value() == 'quick':
            return queryset.filter(cooking_time__lt=QUICK_COOKING)
        elif self.value() == 'medium':
            return queryset.filter(
                cooking_time__gte=QUICK_COOKING,
                cooking_time__lte=MEDIUM_COOKING
            )
        elif self.value() == 'long':
            return queryset.filter(cooking_time__gt=MEDIUM_COOKING)
        return queryset


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'cooking_time', 'image_tag', 'author', 'pub_date',
        'tags_pile', 'products_pile',
        'favorites_count', 'shopping_count'
    )
    list_editable = ('name',)
    search_fields = ('name', 'author',)
    list_filter = ('tags', RecipeAuthorFilter, CookingTimeFilter)
    list_display_links = ('id',)
    inlines = (ProductInline,)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related(
            'tags',
            Prefetch(
                'products',
                queryset=Product.objects.select_related('ingredient')
            )
        ).annotate(
            favorites_count=Count('favoriterecipes'),
            shopping_count=Count('shoppingrecipes')
        )
        return queryset

    @admin.display(description='Теги')
    def tags_pile(self, recipe):
        tags = recipe.tags.all()
        return mark_safe('<br>'.join([tag.name for tag in tags]))

    @admin.display(description='Продукты')
    def products_pile(self, recipe):
        products = recipe.products.all()
        product_list = [
            f'{product.ingredient.name}'
            f'({product.ingredient.measurement_unit}) - '
            f'{product.amount}'
            for product in products
        ]
        return mark_safe('<br>'.join(product_list))

    @admin.display(description='Изображение')
    def image_tag(self, recipe):
        return mark_safe(
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
    list_editable = ('name', 'slug',)
    list_display_links = ('id',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit')
    list_editable = ('name', 'measurement_unit',)
    search_fields = ('name',)
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
