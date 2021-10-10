from datetime import datetime, timedelta
from decimal import Decimal

from pytz import utc

from .models import N_DECIMAL_COMPARISON, N_DECIMAL_PLACES


def date_to_str(d):
    return d.strftime("%Y-%m-%d")


def utcdatetime(*args, **kwargs) -> datetime:
    return datetime(*args, **kwargs, tzinfo=utc)


def utcnow() -> datetime:
    return datetime.now(tz=utc)


def decimals_equal(one: Decimal, two: Decimal) -> bool:
    return round(one, N_DECIMAL_COMPARISON) == round(two, N_DECIMAL_COMPARISON)


def round_decimal(x: Decimal) -> Decimal:
    return round(x, N_DECIMAL_PLACES)  # type: ignore


def date_range(init, end):
    assert end >= init
    return [init + timedelta(days=x) for x in range((end - init).days + 1)]
