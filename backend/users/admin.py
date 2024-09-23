from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = (
        'username', 'email', 'first_name', 'last_name', 'avatar'
    )
    search_fields = ('email', 'first_name', 'last_name', 'username')
    list_display_links = ('username',)
