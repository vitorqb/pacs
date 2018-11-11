from pytz import utc
from datetime import datetime


def utcdatetime(*args, **kwargs):
    return datetime(*args, **kwargs, tzinfo=utc)
