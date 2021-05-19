import django.db.models as m
import attr
from datetime import datetime, timedelta
import random
import string
from common.models import full_clean_and_save
import common.utils


def gen_token():
    return ''.join(
        random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits)
        for _ in range(128)
    )


@attr.s()
class TokenFactory():

    _now_fn = attr.ib(default=common.utils.utcnow)
    _gen_token_fn = attr.ib(default=gen_token)
    _duration = attr.ib(default=timedelta(days=1))

    def __call__(self):
        value = self._gen_token_fn()
        valid_until = self._now_fn() + self._duration
        token = Token(value=value, valid_until=valid_until)
        return full_clean_and_save(token)


class TokenQuerySet(m.QuerySet):

    def is_valid_token_value(self, token_value):
        return (
            self
            .filter(value=token_value)
            .filter(valid_until__gt=common.utils.utcnow()).exists()
        )


class Token(m.Model):
    value = m.TextField()
    valid_until = m.DateTimeField()

    objects = TokenQuerySet.as_manager()

    class Meta:
        indexes = [m.Index(fields=['value'])]
