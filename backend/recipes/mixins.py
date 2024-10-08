from django.contrib import admin
from django.db.models import Count
from django.urls import reverse
from django.utils.safestring import mark_safe


class RecipesCountMixin:
    annotate_field = ''
    table_name = ''
    related_field = ''

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if self.annotate_field:
            return queryset.annotate(
                recipes_count=Count(self.annotate_field)
            )
        return queryset

    @mark_safe
    @admin.display(description='Рецептов')
    def recipes_count(self, obj):
        count = getattr(obj, 'recipes_count', 0)
        if count:
            url = reverse(
                f'admin:recipes_{self.table_name}_changelist'
            ) + f'?{self.related_field}__id__exact={obj.id}'
            return f'<a href="{url}">{count}</a>'
        return count
