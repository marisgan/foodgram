import io

from django.contrib.auth import get_user_model
from django.db.models import Count, Exists, OuterRef, Sum, Value, BooleanField
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from djoser.views import UserViewSet
from django_filters.rest_framework import DjangoFilterBackend
from hashids import Hashids
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import (
    AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
)
from rest_framework.response import Response

from recipes.models import (
    FavoriteRecipe, Ingredient, Product, Recipe, ShoppingRecipe,
    Tag, Subscription
)
from recipes.utils import render_shopping_list
from .filters import IngredientFilter, RecipeFilter
from .pagination import PageNumberLimitPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    AvatarSerializer, MemberSerializer,
    MemberWithRecipesSerializer, IngredientSerializer,
    RecipeManageSerializer, RecipeSerializer,
    RecipeMinifiedSerializer, TagSerializer
)


User = get_user_model()

hashids = Hashids(min_length=6, salt='my_salt')


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

    permission_classes = (IsAuthorOrReadOnly, IsAuthenticatedOrReadOnly)
    pagination_class = PageNumberLimitPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def annotate_recipes(self, recipes):
        user = self.request.user
        return (
            recipes.annotate(
                is_favorited=Exists(FavoriteRecipe.objects.filter(
                    user=user, recipe=OuterRef('pk'))),
                is_in_shopping_cart=Exists(ShoppingRecipe.objects.filter(
                    user=user, recipe=OuterRef('pk')))
            ) if user.is_authenticated else
            recipes.annotate(
                is_favorited=Value(False, output_field=BooleanField()),
                is_in_shopping_cart=Value(False, output_field=BooleanField())
            )
        )

    def get_queryset(self):
        recipes = Recipe.objects.select_related('author').prefetch_related(
            'tags', 'ingredients', 'products')

        return self.annotate_recipes(recipes)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RecipeManageSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def handle_favorite_shopping_actions(
            self, request, pk, model, success_remove_msg
    ):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user

        if request.method == 'POST':
            _, created = model.objects.get_or_create(
                user=user, recipe=recipe)
            if created:
                return Response(
                    RecipeMinifiedSerializer(recipe).data,
                    status=status.HTTP_201_CREATED)
            raise ValidationError({'detail': 'Рецепт уже есть в списке'})

        get_object_or_404(model, user=user, recipe=recipe).delete()
        return Response(
            {'detail': success_remove_msg},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated], url_path='favorite')
    def favorite(self, request, pk=None):
        return self.handle_favorite_shopping_actions(
            request, pk, FavoriteRecipe,
            'Рецепт успешно удален из избранного'
        )

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated], url_path='shopping_cart')
    def shopping_cart(self, request, pk=None):
        return self.handle_favorite_shopping_actions(
            request, pk, ShoppingRecipe,
            'Рецепт успешно удален из списка покупок'
        )

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated],
            url_path='download_shopping_cart')
    def download_shopping_cart(self, request):
        user = request.user
        shopping_recipes = Recipe.objects.filter(
            shoppingrecipes__user=user)
        recipes_names = shopping_recipes.values_list('name', flat=True)
        products = (
            Product.objects.filter(recipe__in=shopping_recipes)
            .values('ingredient__name', 'ingredient__measurement_unit')
            .annotate(total_amount=Sum('amount'))
            .order_by('ingredient__name')
        )
        shopping_list_txt = render_shopping_list(products, recipes_names)
        shopping_list_bytes = shopping_list_txt.encode('utf-8')
        shopping_list_io = io.BytesIO()
        shopping_list_io.write(shopping_list_bytes)
        shopping_list_io.seek(0)

        response = FileResponse(
            shopping_list_io, content_type='text/plain; charset=utf-8'
        )
        response[
            'Content-Disposition'] = 'attachment; filename="shopping_list.txt"'
        return response

    @action(detail=True, methods=['get'],
            permission_classes=[AllowAny], url_path='get-link')
    def get_link(self, request, pk=None):
        if not pk:
            return Response(
                {'error': 'Recipe ID not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        short_code = hashids.encode(int(pk))
        relative_url = reverse(
            'recipes:short-link-redirect', args=[short_code])
        full_url = request.build_absolute_uri(relative_url)

        return Response({'short-link': full_url})


class MemberViewSet(UserViewSet):
    """Вьюсет для работы с пользователями."""
    queryset = User.objects.all()
    serializer_class = MemberSerializer
    pagination_class = PageNumberLimitPagination

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'create']:
            return [AllowAny()]
        elif self.action == 'me':
            return [IsAuthenticated()]
        return [IsAuthenticatedOrReadOnly()]

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

    @action(detail=False, methods=['put', 'delete'], url_path='me/avatar',
            permission_classes=(IsAuthenticated,))
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

        if not user.avatar:
            raise ValidationError({'detail': 'У вас нет аватара'})
        user.avatar.delete()
        user.save()
        return Response(
            {'detail': 'Аватар успешно удален'},
            status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated], url_path='subscribe')
    def manage_subscription(self, request, id=None):
        user = request.user
        author = get_object_or_404(User, pk=id)

        if user == author:
            raise ValidationError(
                {'detail': 'Нельзя подписаться на самого себя'})

        if request.method == 'POST':
            if Subscription.objects.filter(
                user=user, author=author
            ).exists():
                raise ValidationError(
                    {'detail': f'Вы уже подписаны на {author.username}'})

            Subscription.objects.create(user=user, author=author)
            return Response(
                MemberWithRecipesSerializer(
                    author, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )

        get_object_or_404(
            Subscription, user=user, author=author).delete()
        return Response(
            {'status': f'Вы отписались от {author.username}'},
            status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated], url_path='subscriptions')
    def subscriptions(self, request):
        user = request.user
        subscriptions = user.subscriptions.select_related('author').annotate(
            recipes_count=Count('author__recipes'),
            is_subscribed=Value(True, output_field=BooleanField())
        )
        authors = [subscription.author for subscription in subscriptions]
        paginator = PageNumberLimitPagination()
        paginated_subscriptions = paginator.paginate_queryset(
            authors, request
        )
        return paginator.get_paginated_response(
            MemberWithRecipesSerializer(
                paginated_subscriptions,
                context={'request': request},
                many=True).data
        )
