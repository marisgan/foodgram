from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.BasePermission):
    """Разрешение для редактирования данных только для автора рецепта."""

    def has_object_permission(self, request, view, obj):
        return (
            request.method in permissions.SAFE_METHODS
            or obj.author == request.user
        )


class IsOwner(permissions.BasePermission):
    """Разрешение для редактирования данных только для самого пользователя."""

    def has_object_permission(self, request, view, obj):
        return obj == request.user
