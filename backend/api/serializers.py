from collections import Counter

from django.contrib.auth import get_user_model
from djoser.serializers import UserSerializer, UserCreateSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from recipes.models import (
    FavoriteRecipe, ShoppingRecipe, Ingredient, Product, Recipe, Subscription, Tag
)
from recipes.constants import MIN_INGREDIENT_AMOUNT, MIN_COOKING_TIME


User = get_user_model()


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True, allow_null=False)

    class Meta:
        model = User
        fields = ('avatar',)


class MemberSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(read_only=True)

    class Meta(UserSerializer.Meta):
        model = User
        fields = UserSerializer.Meta.fields + (
            'username', 'first_name', 'last_name',
            'is_subscribed', 'avatar'
        )
        read_only_fields = ('is_subscribed', 'avatar')

    def get_is_subscribed(self, author):
        def calculate_is_subscribed():
            request = self.context.get('request')
            current_user = request.user if request else None

            return (
                current_user
                and current_user.is_authenticated
                and current_user != author
                and Subscription.objects.filter(
                    user=current_user, author=author).exists()
            )

        return (
            author.is_subscribed if hasattr(author, 'is_subscribed') else
            calculate_is_subscribed()
        )


class MemberCreateSerializer(UserCreateSerializer):

    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = UserCreateSerializer.Meta.fields + (
            'username', 'first_name', 'last_name',
        )


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class ProductSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        read_only=True, source='ingredient')
    name = serializers.CharField(
        source='ingredient.name', read_only=True)
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit', read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    author = MemberSerializer(read_only=True)
    ingredients = ProductSerializer(
        source='products', many=True, read_only=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )

    def calculate_favorite_shopping(self, recipe, model):
        request = self.context.get('request')
        current_user = request.user if request else None

        return (
            current_user
            and current_user.is_authenticated
            and model.objects.filter(
                user=current_user, recipe=recipe).exists()
        )

    def get_is_favorited(self, recipe):
        return (
            recipe.is_favorited if hasattr(recipe, 'is_favorited') else
            self.calculate_favorite_shopping(recipe, FavoriteRecipe)
        )

    def get_is_in_shopping_cart(self, recipe):
        return (
            recipe.is_in_shopping_cart if hasattr(
                recipe, 'is_in_shopping_cart') else
            self.calculate_favorite_shopping(recipe, ShoppingRecipe)
        )


class RecipeMinifiedSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = fields


class ProductCreateSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(), source='ingredient'
    )
    amount = serializers.IntegerField()

    class Meta:
        model = Product
        fields = ('id', 'amount')

    def validate_amount(self, value):
        if value < MIN_INGREDIENT_AMOUNT:
            raise serializers.ValidationError(
                'Количество ингредиента не может быть меньше '
                f'{MIN_INGREDIENT_AMOUNT}!'
            )
        return value


class RecipeManageSerializer(serializers.ModelSerializer):
    ingredients = ProductCreateSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all()
    )
    image = Base64ImageField(required=True)
    cooking_time = serializers.IntegerField(required=True, allow_null=False)

    class Meta:
        model = Recipe
        fields = (
            'ingredients', 'tags', 'image', 'name', 'text',
            'cooking_time'
        )

    def validate_cooking_time(self, value):
        if value < MIN_COOKING_TIME:
            raise serializers.ValidationError(
                'Время приготовления не может быть меньше '
                f'{MIN_COOKING_TIME} минуты!'
            )
        return value

    def is_empty(self, value, field, field_ru):
        if not value:
            raise serializers.ValidationError({
                f'{field}': f'Поле "{field_ru}" обязательно для загрузки!'
            })

    def find_dublicates(self, ids, model, field, field_ru):
        ids_counts = Counter(ids)
        duplicates = [
            id for id, count in ids_counts.items() if count > 1
        ]
        if duplicates:
            duplicate_names = model.objects.filter(
                id__in=duplicates).values_list('name', flat=True)
            names = ', '.join(duplicate_names)
            raise serializers.ValidationError({
                f'{field}': f'Следующие {field_ru} повторяются: {names}'
            })

    def validate(self, data):
        image = data.get('image')
        self.is_empty(image, 'image', 'Фотография')
        tags = data.get('tags')
        self.is_empty(tags, 'tags', 'Теги')
        tag_ids = [tag.id for tag in tags]
        self.find_dublicates(tag_ids, Tag, 'tags', 'Теги')
        ingredients = data.get('ingredients')
        self.is_empty(ingredients, 'ingredients', 'Ингредиенты')
        ingredient_ids = [
            ingredient['ingredient'].id for ingredient in ingredients
        ]
        self.find_dublicates(
            ingredient_ids, Ingredient, 'ingredients', 'Ингредиенты'
        )
        return data

    def to_representation(self, instance):
        return RecipeSerializer(instance, context=self.context).data

    def create_products(self, ingredients_data, recipe):
        Product.objects.bulk_create([
            Product(
                recipe=recipe,
                ingredient=ingredient_item['ingredient'],
                amount=ingredient_item['amount']
            ) for ingredient_item in ingredients_data
        ])

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)
        self.create_products(ingredients_data, recipe)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)
        instance = super().update(instance, validated_data)

        if tags_data:
            instance.tags.set(tags_data)

        if ingredients_data:
            Product.objects.filter(recipe=instance).delete()
            self.create_products(ingredients_data, instance)

        return instance


class MemberWithRecipesSerializer(MemberSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(MemberSerializer.Meta):
        model = User
        fields = MemberSerializer.Meta.fields + ('recipes', 'recipes_count')

    def get_recipes(self, author):
        request = self.context.get('request')
        recipes_limit = int(request.query_params.get('recipes_limit', 10**10))
        recipes = author.recipes.all()[:recipes_limit]
        return RecipeMinifiedSerializer(recipes, many=True).data

    def get_recipes_count(self, author):
        return (
            author.recipes_count if hasattr(author, 'recipes_count') else
            author.recipes.count()
        )
