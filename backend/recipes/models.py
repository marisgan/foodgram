from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from .constants import (
    MAX_LENGTH_EMAIL, MAX_LENGTH_INGREDIENT_NAME, MAX_LENGTH_NAME,
    MAX_LENGHT_TAG, MAX_LENGTH_UNIT,
    MAX_LENGTH_RECIPE_NAME, MIN_COOKING_TIME, MIN_INGREDIENT_AMOUNT
)
from .validators import validate_username


class Member(AbstractUser):
    """Кастомизированная модель пользователя."""

    email = models.EmailField(unique=True, max_length=MAX_LENGTH_EMAIL)
    username = models.CharField(
        validators=[validate_username],
        max_length=MAX_LENGTH_NAME, unique=True)
    first_name = models.CharField(max_length=MAX_LENGTH_NAME)
    last_name = models.CharField(max_length=MAX_LENGTH_NAME)
    avatar = models.ImageField(
        upload_to='users/images/', null=True, default=None
    )

    class Meta:
        ordering = ('username',)
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username


User = get_user_model()


class Subscription(models.Model):
    """Подписка пользователя на других пользователей."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='subscriptions',
        verbose_name='Пользователь'
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='subscribers',
        verbose_name='Автор'
    )

    class Meta:
        ordering = ('author',)
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'], name='unique_subscription')
        ]
        verbose_name = 'подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        return f'{self.user} подписан на {self.author}'

    def clean(self):
        if self.user == self.author:
            raise ValidationError('Нельзя подписаться на самого себя')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class RelatedName:
    """Дефолтное имя для полей связи."""

    class Meta:
        default_related_name = '%(class)ss'


class Tag(models.Model):
    """Теги."""

    name = models.CharField('Название тега', max_length=MAX_LENGHT_TAG)
    slug = models.SlugField('Слаг', unique=True, max_length=MAX_LENGHT_TAG)

    class Meta:
        ordering = ('name',)
        verbose_name = 'тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """Ингредиенты."""

    name = models.CharField('Название', max_length=MAX_LENGTH_INGREDIENT_NAME)
    measurement_unit = models.CharField(
        'Единица измерения', max_length=MAX_LENGTH_UNIT)

    class Meta(RelatedName.Meta):
        ordering = ('name',)
        verbose_name = 'ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return f'{self.name}, {self.measurement_unit}'


class Recipe(models.Model):
    """Рецепты."""

    name = models.CharField('Название', max_length=MAX_LENGTH_RECIPE_NAME)
    text = models.TextField('Описание рецепта')
    cooking_time = models.SmallIntegerField(
        'Время приготовления в минутах',
        validators=[MinValueValidator(
            MIN_COOKING_TIME,
            message=(
                'Время приготовления не может быть меньше '
                f'{MIN_COOKING_TIME}'
            )
        )]
    )
    image = models.ImageField(
        'Фотография', upload_to='recipes/images/', blank=False, null=False
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name='Автор')
    tags = models.ManyToManyField(Tag, verbose_name='Тэги')
    ingredients = models.ManyToManyField(
        Ingredient, through='Product', verbose_name='Ингредиенты')
    pub_date = models.DateTimeField('Дата публикации', auto_now_add=True)

    class Meta(RelatedName.Meta):
        ordering = ('-pub_date',)
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class Product(models.Model):
    """Модель для связи рецепта с ингедиентом и количеством продукта"""

    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE,)
    amount = models.SmallIntegerField(
        'Количество ингредиента',
        default=MIN_INGREDIENT_AMOUNT,
        validators=[MinValueValidator(
            MIN_INGREDIENT_AMOUNT,
            message=(
                'Количество ингредиента не может быть меньше '
                f'{MIN_INGREDIENT_AMOUNT}'
            )
        )]
    )

    class Meta(RelatedName.Meta):
        verbose_name = 'продукт'
        verbose_name_plural = 'Продукты'

    def __str__(self):
        return (
            f'{self.ingredient.name} - {self.amount} '
            f'{self.ingredient.measurement_unit} '
            f'для рецепта {self.recipe}'
        )


class UserRecipe(models.Model):
    """Абстрактная модель для связи пользователя с рецептом"""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )

    class Meta(RelatedName.Meta):
        abstract = True
        ordering = ('recipe',)

    def __str__(self):
        return f'{self.user} {self.recipe}'


class ShoppingRecipe(UserRecipe):
    """Модель для связи пользователя с рецептом в списке покупок"""

    class Meta(UserRecipe.Meta):
        """Наследует имена для связи, валидацию"""
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'], name='user_shopping_recipe')
        ]
        verbose_name = 'рецепт в списке покупок'
        verbose_name_plural = 'Рецепты в списке покупок'


class FavoriteRecipe(UserRecipe):
    """Модель для связи пользователя с рецептом в избранном"""

    class Meta(UserRecipe.Meta):
        """Наследует имена для связи, сортировку"""
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'], name='user_favorite_recipe')
        ]
        verbose_name = 'рецепт в избранном'
        verbose_name_plural = 'Рецепты в избранном'
