from django.contrib.auth import get_user_model
from django.db.models import Count, Exists, OuterRef, Sum, Value, BooleanField
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.serializers import SetPasswordSerializer
from djoser.views import UserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from rest_framework.permissions import (
    AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
)

from recipes.models import (
    FavoriteRecipe, Ingredient, Product, Recipe, ShoppingRecipe, Tag
)
from users.models import Subscription
from .filters import IngredientFilter, RecipeFilter
from .pagination import PageNumberLimitPagination
from .permissions import IsAuthorOrReadOnly, IsOwner
from .serializers import (
    AvatarSerializer, CustomUserSerializer, CustomUserCreateSerializer,
    CustomUserWithRecipesSerializer, EmptySerializer, IngredientSerializer,
    RecipeCreateSerializer, RecipeResponseSerializer,
    RecipeMinifiedSerializer, TagSerializer
)


User = get_user_model()


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для тегов (только list и detail)"""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для отображения ингредиентов (только list и detail)"""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ['^name']
    filterset_fields = ('name',)
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для CRUD операций для рецептов"""

    queryset = Recipe.objects.all()
    serializer_class = RecipeResponseSerializer
    permission_classes = (IsAuthorOrReadOnly, IsAuthenticatedOrReadOnly)
    pagination_class = PageNumberLimitPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def annotate_recipes(self, queryset):
        user = self.request.user
        annotated_recipes = queryset
        if user.is_authenticated:
            annotated_recipes = queryset.annotate(
                is_favorited=Exists(FavoriteRecipe.objects.filter(
                    user=user, recipe=OuterRef('pk'))),
                is_in_shopping_cart=Exists(ShoppingRecipe.objects.filter(
                    user=user, recipe=OuterRef('pk')))
            )
        else:
            annotated_recipes = queryset.annotate(
                is_favorited=Value(False, output_field=BooleanField()),
                is_in_shopping_cart=Value(False, output_field=BooleanField())
            )
        return annotated_recipes

    def get_queryset(self):
        queryset = Recipe.objects.select_related('author').prefetch_related(
            'tags', 'ingredients', 'products')

        return self.annotate_recipes(queryset)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RecipeCreateSerializer
        elif self.action == 'favorite' or self.action == 'shopping_cart':
            return EmptySerializer
        return super().get_serializer_class()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action == 'retrieve':
            context['recipe'] = self.get_object()
        elif self.action == 'list':
            context['recipes'] = self.get_queryset()
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        recipe = self.annotate_recipes(
            Recipe.objects.filter(pk=serializer.instance.pk)).first()

        response_serializer = RecipeResponseSerializer(
            recipe,
            context={
                'request': request,
                'recipe': recipe,
                'is_subscribed': False})
        return Response(
            response_serializer.data, status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        recipe = self.annotate_recipes(
            Recipe.objects.prefetch_related('products__ingredient'
                                            ).filter(pk=instance.pk)).first()

        response_serializer = RecipeResponseSerializer(
            recipe, context={'request': request, 'recipe': recipe}
        )
        return Response(
            response_serializer.data, status=status.HTTP_200_OK
        )

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def handle_action(
            self, request, pk, model, success_add_msg, success_remove_msg
    ):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user

        if request.method == 'POST':
            instance, created = model.objects.get_or_create(
                user=user, recipe=recipe)
            if created:
                serializer = RecipeMinifiedSerializer(recipe)
                return Response(
                    serializer.data,
                    status=status.HTTP_201_CREATED)
            return Response(
                {'detail': 'Рецепт уже есть в списке'},
                status=status.HTTP_400_BAD_REQUEST)

        elif request.method == 'DELETE':
            instance = model.objects.filter(user=user, recipe=recipe)
            if instance.exists():
                instance.delete()
                return Response(
                    {'detail': success_remove_msg},
                    status=status.HTTP_204_NO_CONTENT)
            return Response(
                {'detail': 'Рецепта нет в списке'},
                status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated], url_path='favorite')
    def favorite(self, request, pk=None):
        return self.handle_action(
            request, pk, FavoriteRecipe,
            'Рецепт успешно добавлен в избранное',
            'Рецепт успешно удален из избранного'
        )

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated], url_path='shopping_cart')
    def shopping_cart(self, request, pk=None):
        return self.handle_action(
            request, pk, ShoppingRecipe,
            'Рецепт успешно добавлен в список покупок',
            'Рецепт успешно удален из списка покупок'
        )

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated],
            url_path='download_shopping_cart')
    def download_shopping_cart(self, request):
        user = request.user
        shopping_recipes = Recipe.objects.filter(
            shoppingrecipes__user=user)
        shopping_list = (
            Product.objects.filter(recipe__in=shopping_recipes)
            .values('ingredient__name', 'ingredient__measurement_unit')
            .annotate(total_amount=Sum('amount'))
            .order_by('ingredient__name')
        )

        shopping_list_txt = "Список покупок:\n\n"
        for item in shopping_list:
            shopping_list_txt += (
                f'{item['ingredient__name']} '
                f'({item['ingredient__measurement_unit']}) — '
                f'{item['total_amount']}\n'
            )

        response = HttpResponse(
            shopping_list_txt, content_type='text/plain; charset=utf-8')
        response[
            'Content-Disposition'] = 'attachment; filename="shopping_list.txt"'

        return response

    @action(detail=True, methods=['get'],
            permission_classes=[AllowAny], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        relative_url = f'/s/{recipe.short_id}/'
        short_link = request.build_absolute_uri(relative_url)

        return Response({'short-link': short_link.replace("/api", "")})


class CustomUserViewSet(UserViewSet):
    """Вьюсет для работы с пользователями."""
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = (IsOwner, IsAuthenticatedOrReadOnly,)
    pagination_class = PageNumberLimitPagination

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'create']:
            return [AllowAny()]
        return [IsOwner(), IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        return (
            User.objects.annotate(is_subscribed=Exists(
                Subscription.objects.filter(
                    user=user, author=OuterRef('pk'))
            )) if user.is_authenticated else
            User.objects.annotate(is_subscribed=Value(
                False, output_field=BooleanField()
            ))
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return CustomUserCreateSerializer
        elif self.action == 'set_password':
            return SetPasswordSerializer
        elif self.action == 'manage_avatar':
            return AvatarSerializer
        elif self.action == 'manage_subscription':
            return EmptySerializer
        return CustomUserSerializer

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated], url_path='me')
    def me(self, request):
        user = request.user
        user = User.objects.annotate(is_subscribed=Value(
            False, output_field=BooleanField()
        )).get(pk=user.pk)
        serializer = CustomUserSerializer(user, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'delete'], url_path='me/avatar',
            permission_classes=(IsOwner,))
    def manage_avatar(self, request):
        user = request.user
        if request.method == 'PUT':
            serializer = AvatarSerializer(
                data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            user.avatar = serializer.validated_data['avatar']
            user.save()
            response_serializer = AvatarSerializer(
                request.user, context={'request': request})
            return Response(
                response_serializer.data,
                status=status.HTTP_200_OK)

        elif request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete()
                user.save()
                return Response(
                    {'detail': 'Аватар успешно удален'},
                    status=status.HTTP_204_NO_CONTENT)
            return Response({'detail': 'У вас нет аватара'},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated], url_path='subscribe')
    def manage_subscription(self, request, id=None):
        user = request.user
        author = get_object_or_404(User, pk=id)

        if user == author:
            return Response(
                {'detail': 'Нельзя подписаться на самого себя'},
                status=status.HTTP_400_BAD_REQUEST)

        if request.method == 'POST':
            if Subscription.objects.filter(
                user=user, author=author
            ).exists():
                return Response(
                    {'detail': 'Вы уже подписаны на этого пользователя'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            Subscription.objects.create(user=user, author=author)
            author = User.objects.filter(pk=author.pk).annotate(
                recipes_count=Count('recipes'),
                is_subscribed=Value(True, output_field=BooleanField())
            ).first()
            recipes_limit = request.query_params.get('recipes_limit')
            response_serializer = CustomUserWithRecipesSerializer(
                author,
                context={
                    'recipes_limit': recipes_limit,
                    'recipes_count': author.recipes_count,
                    'is_subscribed': author.is_subscribed
                }
            )
            return Response(
                response_serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == 'DELETE':
            subscription = Subscription.objects.filter(
                user=user, author=author)
            if not subscription.exists():
                return Response(
                    {'detail': 'Вы не подписаны на этого пользователя'},
                    status=status.HTTP_400_BAD_REQUEST)

            subscription.delete()
            return Response(
                {'status': f'Вы отписались от {author.username}'},
                status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'],
            permission_classes=[IsOwner], url_path='subscriptions')
    def subscriptions(self, request):
        user = request.user
        subscriptions = user.subscriptions.select_related('author').annotate(
            recipes_count=Count('author__recipes'),
            is_subscribed=Value(True, output_field=BooleanField())
        )
        paginator = PageNumberLimitPagination()
        paginated_subscriptions = paginator.paginate_queryset(
            subscriptions, request
        )
        response_data = []
        recipes_limit = request.query_params.get('recipes_limit')

        for subscription in paginated_subscriptions:
            user_data = CustomUserWithRecipesSerializer(
                subscription.author,
                context={
                    'recipes_limit': recipes_limit,
                    'recipes_count': subscription.recipes_count,
                    'is_subscribed': subscription.is_subscribed
                }
            ).data
            response_data.append(user_data)

        return paginator.get_paginated_response(response_data)
