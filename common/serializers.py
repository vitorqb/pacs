from .models import MinValueValidator, N_DECIMAL_MAX_DIGITS, N_DECIMAL_PLACES
from rest_framework import serializers


def new_price_field():
    """ Returns a Fied to be used as price """
    return serializers.DecimalField(
        validators=[MinValueValidator(0, "Prices must be positive")],
        max_digits=N_DECIMAL_MAX_DIGITS,
        decimal_places=N_DECIMAL_PLACES
    )
