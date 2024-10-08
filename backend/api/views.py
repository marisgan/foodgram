from django.core.files.base import ContentFile
from django.db.models import Count, Exists, OuterRef, Sum, Value, BooleanField
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.encoding import smart_bytes
from djoser.views import UserViewSet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import (
    AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
)
from rest_framework.response import Response

from recipes.models import (
    FavoriteRecipe, Ingredient, Product, Recipe, RecipeShortLink,
    ShoppingRecipe, Subscription, Tag, User
)
from .filters import IngredientFilter, RecipeFilter
from .pagination import PageNumberLimitPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    AvatarSerializer, MemberSerializer,
    MemberWithRecipesSerializer, IngredientSerializer,
    RecipeWriteSerializer, RecipeSerializer,
    RecipeMinifiedSerializer, TagSerializer
)
from .utils import (
    generate_unique_short_code, render_shopping_list
)


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
            return RecipeWriteSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @staticmethod
    def handle_favorite_shopping_actions(
            request, pk, model, success_remove_msg
    ):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user

        if request.method == 'DELETE':
            get_object_or_404(model, user=user, recipe=recipe).delete()
            return Response(
                {'detail': success_remove_msg},
                status=status.HTTP_204_NO_CONTENT
            )

        _, created = model.objects.get_or_create(
            user=user, recipe=recipe)
        if not created:
            raise ValidationError({'detail': 'Рецепт уже есть в списке'})
        return Response(
            RecipeMinifiedSerializer(recipe).data,
            status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated], url_path='favorite')
    def favorite(self, request, pk=None):
        return RecipeViewSet.handle_favorite_shopping_actions(
            request, pk, FavoriteRecipe,
            'Рецепт успешно удален из избранного'
        )

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated], url_path='shopping_cart')
    def shopping_cart(self, request, pk=None):
        return RecipeViewSet.handle_favorite_shopping_actions(
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
        products = (
            Product.objects.filter(recipe__in=shopping_recipes)
            .values('ingredient__name', 'ingredient__measurement_unit')
            .annotate(total_amount=Sum('amount'))
            .order_by('ingredient__name')
        )
        shopping_list = smart_bytes(
            render_shopping_list(products, shopping_recipes)
        )

        return FileResponse(
            ContentFile(shopping_list),
            as_attachment=True,
            filename='shopping_list.txt',
            content_type='text/plain; charset=utf-8'
        )

    @action(detail=True, methods=['get'],
            permission_classes=[AllowAny], url_path='get-link')
    def get_link(self, request, pk=None):
        if not Recipe.objects.filter(pk=pk).exists():
            raise ValidationError({'detail': f'Рецепта {pk} не существует'})
        recipe = get_object_or_404(Recipe, pk=pk)
        short_link, created = RecipeShortLink.objects.get_or_create(
            recipe=recipe
        )
        if created:
            short_link.short_code = generate_unique_short_code()
            short_link.save()
        relative_url = reverse(
            'recipes:short-link-redirect', args=[short_link.short_code])
        full_url = request.build_absolute_uri(relative_url)
        return Response({'short-link': full_url})


class MemberViewSet(UserViewSet):
    """Вьюсет для работы с пользователями."""
    permission_classes = (IsAuthenticatedOrReadOnly, )
    queryset = User.objects.all()
    serializer_class = MemberSerializer
    pagination_class = PageNumberLimitPagination

    def get_permissions(self):
        if self.action == 'me':
            return [IsAuthenticated()]
        return super().get_permissions()

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

        if request.method == 'DELETE':
            get_object_or_404(
                Subscription, user=user, author=author
            ).delete()
            return Response(
                {'status': f'Вы отписались от {author.username}'},
                status=status.HTTP_204_NO_CONTENT)

        _, created = Subscription.objects.get_or_create(
            user=user, author=author)
        if not created:
            raise ValidationError(
                {'detail': f'Вы уже подписаны на {author.username}'})
        return Response(
            MemberWithRecipesSerializer(
                author, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

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
