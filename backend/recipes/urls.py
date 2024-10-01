from django.urls import path

from .views import redirect_to_recipe


app_name = 'recipes'

urlpatterns = [
    path('<str:short_code>/', redirect_to_recipe, name='short-link-redirect'),
]
