#  Проект Foodgram

## О проекте

Социальная сеть «Фудграм» для любителей готовить и пробовать новые рецепты.
На сайте пользователи могут публиковать свои рецепты, добавлять чужие рецепты в избранное и подписываться на публикации других авторов. Зарегистрированным пользователям доступен сервис «Список покупок». Он позволит создавать список продуктов, которые нужно купить для приготовления выбранных блюд. Для каждого рецепта можно получить прямую короткую ссылку, которая не меняется после редактирования рецепта.

## Стек

- Python
- Django REST Framework
- PostgreSQL
- React
- Docker
- Nginx
- Gunicorn
- CI/CD GitHub Actions

### Как запустить проект через Docker:

1. Клонируйте репозиторий проекта
2. Установите и запустите докер
3. В корне проекта нужно создать файл .env и заполнить его (см.ниже)
4. Перейдите в папку infra и выполните команды в терминале:
```
docker compose -f docker-compose.production.yml up 
docker compose -f docker-compose.production.yml exec backend python manage.py migrate
docker compose -f docker-compose.production.yml exec backend python manage.py collectstatic
docker compose -f docker-compose.production.yml exec backend cp -r /app/collected_static/. /backend_static/static/
```
### Как заполнить файл ```.env```:

Нужно создать файл .env в корне проекта и указать в нем следующие переменные:

```
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=
DB_NAME=
DB_HOST=
DB_PORT=
DJANGO_SECRET_KEY=
DJANGO_DEBUG=True
ALLOWED_HOSTS=
```

### Как запустить бэкенд локально без Docker:
1. Создайте виртуальное окружение:
```python -m venv venv```
2. Установите зависимости:
```pip install -r requirements.txt```
3. Перейдите в папку backend и в терминале введите команду:
```python manage.py runserver```
```python manage.py migrate```

### Команды импорта данных (тегов и ингредиентов):
```
python manage.py import_ingredients
python manage.py import_tags
```

### Автор
Финальное задание курса Python Backend Developer Яндекс Практикума. Выполнила Марина Асташова (marisgan@gmail.com)

