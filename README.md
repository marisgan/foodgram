[![Main Foodgram workflow](https://github.com/marisgan/foodgram/actions/workflows/main.yml/badge.svg)](https://github.com/marisgan/foodgram/actions/workflows/main.yml)

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
1. Клонируйте репозиторий:
```git clone https://github.com/marisgan/foodgram.git```
2. В корне проекта создайте файл .env и укажите в нем следующие переменные:
```
- DJANGO_SECRET_KEY='your-secret-key'
- DJANGO_DEBUG=True
```
3. Перейдите в папку backend:
```cd backend```
4. Создайте виртуальное окружение:
```python -m venv venv```
5. Установите зависимости:
```pip install -r requirements.txt```
6. Выполните миграции:
```python manage.py migrate```
7. Импортируйте данные:
```
python manage.py import_ingredients
python manage.py import_tags
```
8. Запустите проект:
```python manage.py runserver```

### Справка по проекту
[Документация API](https://foodgram.marisgan.com/api/docs/)

### Автор
Финальное задание курса [Python Backend Developer Яндекс Практикум](https://practicum.yandex.ru/backend-developer-ab/)

Выполнила  [Марина Асташова](https://github.com/marisgan)

