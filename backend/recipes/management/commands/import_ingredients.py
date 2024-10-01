import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Импортирует ингредиенты из файла data/ingredients.json'

    def handle(self, *args, **kwargs):
        file_path = os.path.join(
            settings.BASE_DIR, '..', 'data', 'ingredients.json')

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                ingredients_data = json.load(file)

            for ingredient in ingredients_data:
                Ingredient.objects.get_or_create(
                    name=ingredient['name'],
                    measurement_unit=ingredient['measurement_unit'],
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f'Ингредиенты успешно импортированы из {file_path}!'))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Файл не найден: {file_path}'))
        except json.JSONDecodeError:
            self.stdout.write(
                self.style.ERROR(
                    'Ошибка при чтении JSON файла. Проверьте его формат.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка: {e}'))
