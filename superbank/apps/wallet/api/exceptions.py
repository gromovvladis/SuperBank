from rest_framework import serializers


class RestApiException(serializers.ValidationError):
    status_code = 400
    default_detail = ""
    default_error_key = "error"

    _message_key = "detail"
    _message_value = "https://rutube.ru/video/c6cc4d620b1d4338901770a44b3e82f4/"

    def __init__(self, msg, *args, **kwargs):
        detail = msg if msg else self.default_detail
        super().__init__(detail, *args, **kwargs)
        self.detail = {
            self.default_error_key: detail,
            self._message_key: self._message_value,
        }


class InvalidAmountException(RestApiException):
    default_detail = "Некорректная сумма"


class InvalidTypeException(RestApiException):
    default_detail = "Некорректный тип транзации"
