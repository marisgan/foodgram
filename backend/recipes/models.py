import hashlib
import random

from django.contrib.auth import get_user_model
from django.db import models

from .constants import (
    MAX_LENGTH_INGREDIENT_NAME, MAX_LENGHT_TAG, MAX_LENGTH_UNIT,
    MAX_LENGTH_RECIPE_NAME
)


User = get_user_model()


class RelatedName:
    """Имя для связанных моделей."""

    class Meta:
        default_related_name = '%(class)ss'


class Tag(models.Model):
    """Тэги."""

    name = models.CharField('Название тэга', max_length=MAX_LENGHT_TAG)
    slug = models.SlugField(unique=True, max_length=MAX_LENGHT_TAG)

    class Meta:
        ordering = ('name',)
        verbose_name = 'тэг'
        verbose_name_plural = 'Тэги'

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
    cooking_time = models.SmallIntegerField('Время приготовления в минутах')
    image = models.ImageField('Фотография', upload_to='recipes/images/')
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name='Автор')
    tags = models.ManyToManyField(Tag, verbose_name='Тэги')
    ingredients = models.ManyToManyField(
        Ingredient, through='Product', verbose_name='Ингредиенты')
    short_id = models.CharField(
        'Идентификатор для короткой ссылки',
        max_length=10, unique=True, blank=True, null=True)

    class Meta(RelatedName.Meta):
        ordering = ('name',)
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name

    def generate_unique_short_id(self):
        while True:
            short_id = hashlib.md5(str(self.id).encode()).hexdigest()[:6]
            if not Recipe.objects.filter(short_id=short_id).exists():
                return short_id
            self.id = f"{self.id}{random.randint(0, 1000)}"

    def save(self, *args, **kwargs):
        if not self.id:
            super().save(*args, **kwargs)
        if not self.short_id:
            self.short_id = self.generate_unique_short_id()
            self.save(update_fields=['short_id'])
        else:
            super().save(*args, **kwargs)


class Product(models.Model):
    """Модель для связи рецепта с ингедиентом и количеством продукта"""

    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE,)
    amount = models.SmallIntegerField('Количество ингредиента', default=1)

    class Meta(RelatedName.Meta):
        verbose_name = 'продукт'
        verbose_name_plural = 'Продукты'

    def __str__(self):
        return (
            f'{self.ingredient.name} - {self.amount} '
            f'{self.ingredient.measurement_unit} '
            f'для рецепта {self.recipe}'
        )


class ShoppingRecipe(models.Model):
    """Модель для связи пользователя с рецептом в списке покупок"""
    user = models.ForeignKey(User, on_delete=models.CASCADE,)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)

    class Meta(RelatedName.Meta):
        ordering = ('recipe',)

    def __str__(self):
        return f'{self.user} {self.shopping_recipe}'


class FavoriteRecipe(models.Model):
    """Модель для связи пользователя с рецептом в избранном"""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)

    class Meta(RelatedName.Meta):
        ordering = ('recipe',)

    def __str__(self):
        return f'{self.user} {self.recipe}'
