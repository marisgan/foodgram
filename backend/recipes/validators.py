import re

from django.core.exceptions import ValidationError


def validate_username(username):
    invalid_chars = re.findall(r'[^\w.@+-]', username)
    if invalid_chars:
        invalid_chars_formatted = ', '.join(map(repr, set(invalid_chars)))
        raise ValidationError(
            'Имя пользователя содержит недопустимые символы: '
            f'{invalid_chars_formatted}'
        )
    return username
