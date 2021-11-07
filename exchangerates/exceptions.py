from rest_framework.exceptions import APIException


class NotEnoughData(APIException):
    status_code = 400
    default_code = 'not_enough_data'


class ExchangeRateAlreadyExists(APIException):
    status_code = 400
    default_code = 'exchangerate_already_exists'
