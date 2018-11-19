from decimal import Decimal
from pyrsistent import pvector
import django.db.models as m
from django.core.validators import MinValueValidator
from copy import deepcopy


N_DECIMAL_PLACES = 5
DECIMAL_PLACES = Decimal('10') ** -N_DECIMAL_PLACES


def new_cents_field():
    """ Returns a new field to be used as cents """
    return m.DecimalField(max_digits=20, decimal_places=N_DECIMAL_PLACES)


def new_price_field():
    """ Returns a Fied to be used as price """
    return m.DecimalField(
        validators=[MinValueValidator(0, "Prices must be positive")],
        max_digits=20,
        decimal_places=N_DECIMAL_PLACES
    )


class NameField(m.CharField):
    """ Fields for names """
    MAX_LENGTH = 150

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = self.MAX_LENGTH
        kwargs['unique'] = True
        super().__init__(*args, **kwargs)


def full_clean_and_save(x):
    x.full_clean()
    x.save()
    return x


def extract_pks(x):
    return pvector(x.values_list('pk', flat=True))


def list_to_queryset(lst):
    """ Converts a list of objects into a queryset. """
    if len(lst) == 0:
        return m.QuerySet().none()
    return type(lst[0]).objects.filter(pk__in=[x.pk for x in lst])
