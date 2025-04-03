from rest_framework import serializers


class RestApiException(serializers.ValidationError):
    status_code = 400
    default_detail = ""
    default_error_key = "error"

    def __init__(self, msg, *args, **kwargs):
        detail = msg if msg else self.default_detail
        super().__init__(detail, *args, **kwargs)
        self.detail = {self.default_error_key: detail}


class InvalidAmountException(RestApiException):
    default_detail = "Некорректная сумма"


class InvalidTypeException(RestApiException):
    default_detail = "Некорректный тип транзации"
