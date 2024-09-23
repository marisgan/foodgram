from django.contrib.auth.validators import UnicodeUsernameValidator

from django.core.exceptions import ValidationError


def validate_username(username):
    if username == 'me':
        raise ValidationError(
            'me - недопустимое имя пользователя!'
        )


username_validator = UnicodeUsernameValidator()
