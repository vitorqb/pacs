from datetime import datetime
from decimal import Decimal

from pytz import utc

from .models import N_DECIMAL_COMPARISON, N_DECIMAL_PLACES


def utcdatetime(*args, **kwargs) -> datetime:
    return datetime(*args, **kwargs, tzinfo=utc)


def decimals_equal(one: Decimal, two: Decimal) -> bool:
    return round(one, N_DECIMAL_COMPARISON) == round(two, N_DECIMAL_COMPARISON)


def round_decimal(x: Decimal) -> Decimal:
    return round(x, N_DECIMAL_PLACES)  # type: ignore
