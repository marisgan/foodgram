import csv

from django.core.management import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    """Команда для заполнения базы данных."""

    help = 'Loads data from a CSV file into the database.'

    def add_arguments(self, parser):
        # Добавляем аргумент для пути к CSV файлу
        parser.add_argument('csv_file', type=str, help='Path to the CSV file.')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']

        # Открываем CSV файл
        with open(csv_file, newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)  # Пропускаем заголовок (первую строку)

            for row in reader:
                # Предположим, что твоя модель YourModel имеет поля name и description
                name, unit = row
                # Создаём или обновляем запись в базе данных
                Ingredient.objects.create(
                    name=name,
                    unit=unit,
                )

        self.stdout.write(self.style.SUCCESS('Данные успешно загружены'))
