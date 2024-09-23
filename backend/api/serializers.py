import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db.models import QuerySet
from djoser.serializers import UserSerializer, UserCreateSerializer
from rest_framework import serializers

from recipes.models import Ingredient, Product, Recipe, Tag
from users.constants import MAX_LENGTH_NAME
from users.validators import validate_username, username_validator


User = get_user_model()


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]

            data = ContentFile(base64.b64decode(imgstr), name='image.' + ext)

        return super().to_internal_value(data)

    def to_representation(self, value):
        if value:
            request = self.context.get('request')
            url = value.url
            return request.build_absolute_uri(url) if request else url
        return None


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True, allow_null=False)

    class Meta:
        model = User
        fields = ('avatar',)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if instance.avatar and hasattr(instance.avatar, 'url'):
            representation['avatar'] = request.build_absolute_uri(
                instance.avatar.url)
        return representation


class CustomUserSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(read_only=True)

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'avatar'
        )
        read_only_fields = ('is_subscribed', 'avatar')

    def get_is_subscribed(self, obj):
        if 'is_subscribed' in self.context:
            return self.context['is_subscribed']
        return getattr(obj, 'is_subscribed', False)


class CustomUserCreateSerializer(UserCreateSerializer):
    email = serializers.EmailField(max_length=MAX_LENGTH_NAME)
    username = serializers.CharField(
        validators=[username_validator, validate_username],
        max_length=MAX_LENGTH_NAME)
    first_name = serializers.CharField(
        max_length=MAX_LENGTH_NAME)
    last_name = serializers.CharField(
        max_length=MAX_LENGTH_NAME)
    password = serializers.CharField(write_only=True)

    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name', 'password'
        )
        read_only_fields = ('id',)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Этот email уже зарегистрирован')
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                'Это имя пользователя уже зарегистрировано')
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientAmountSerializer(serializers.ModelSerializer):
    amount = serializers.SerializerMethodField()

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit', 'amount')

    def get_amount(self, obj):
        recipe = self.context.get('recipe') or self.context.get('recipes')

        if isinstance(recipe, Recipe):
            product = Product.objects.filter(
                recipe=recipe, ingredient=obj).first()
        elif isinstance(recipe, QuerySet):
            product = Product.objects.filter(
                recipe__in=recipe, ingredient=obj).first()
        else:
            product = None

        return product.amount if product else None


class RecipeResponseSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    author = CustomUserSerializer(
        read_only=True,
        context={'request': serializers.CurrentUserDefault()})
    ingredients = IngredientAmountSerializer(
        many=True, read_only=True, context={'recipe': 'self'})
    is_favorited = serializers.BooleanField(read_only=True)
    is_in_shopping_cart = serializers.BooleanField(read_only=True)
    image = Base64ImageField(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )
        read_only_fields = ('id',)


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    image = Base64ImageField(read_only=True)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = ('id', 'name', 'image', 'cooking_time')


class ProductSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(), source='ingredient'
    )
    amount = serializers.IntegerField()

    class Meta:
        model = Product
        fields = ('id', 'amount')

    def validate_amount(self, value):
        if value < 1:
            raise serializers.ValidationError(
                'Количество ингредиента не может быть меньше 1!')
        return value


class RecipeCreateSerializer(serializers.ModelSerializer):
    ingredients = ProductSerializer(many=True)
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
        if value < 1:
            raise serializers.ValidationError(
                'Время приготовления не может быть меньше 1 минуты!')
        return value

    def validate(self, data):
        ingredients = data.get('ingredients')
        tags = data.get('tags')

        if not ingredients:
            raise serializers.ValidationError(
                'Поле ингредиентов не может быть пустым!')

        if not tags:
            raise serializers.ValidationError(
                'Поле тэгов не может быть пустым!')

        ingredient_ids = [
            ingredient['ingredient'].id for ingredient in ingredients]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                'Ингредиенты не могут повторяться!')

        if len(tags) != len(set(tags)):
            raise serializers.ValidationError('Тэги не могут повторяться!')

        return data

    def to_representation(self, instance):
        return RecipeResponseSerializer(instance).data

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)

        for ingredient_item in ingredients_data:
            Product.objects.create(
                recipe=recipe, ingredient=ingredient_item['ingredient'],
                amount=ingredient_item['amount']
            )
        return recipe

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.image = validated_data.get('image', instance.image)
        instance.cooking_time = validated_data.get(
            'cooking_time', instance.cooking_time
        )
        tags_data = validated_data.get('tags')
        if tags_data:
            instance.tags.set(tags_data)

        ingredients_data = validated_data.pop('ingredients', None)

        if ingredients_data:
            Product.objects.filter(recipe=instance).delete()

            for ingredient_item in ingredients_data:
                Product.objects.create(
                    recipe=instance,
                    ingredient=ingredient_item['ingredient'],
                    amount=ingredient_item['amount']
                )
        instance.save()
        instance.refresh_from_db()
        return instance


class CustomUserWithRecipesSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    avatar = Base64ImageField(read_only=True)

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'recipes', 'recipes_count', 'avatar'
        )

    def get_recipes(self, obj):
        recipes_limit = self.context.get('recipes_limit')
        recipes = (
            obj.recipes.all()[:int(recipes_limit)] if recipes_limit else
            obj.recipes.all()
        )
        return RecipeMinifiedSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        return self.context.get('recipes_count', 0)

    def get_is_subscribed(self, obj):
        return self.context.get('is_subscribed', False)


class EmptySerializer(serializers.Serializer):
    pass
