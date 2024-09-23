from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.db import models

from .constants import MAX_LENGTH_EMAIL, MAX_LENGTH_NAME
from .validators import validate_username, username_validator


class CustomUser(AbstractUser):
    """Кастомизированная модель пользователя."""

    email = models.EmailField(unique=True, max_length=MAX_LENGTH_EMAIL)
    username = models.CharField(
        validators=[username_validator, validate_username],
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
        verbose_name = 'подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        return f'{self.user} подписан на {self.subscribed_to}'
