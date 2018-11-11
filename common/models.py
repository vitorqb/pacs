from pyrsistent import pvector
import django.db.models as m
from django.core.validators import MinValueValidator
from copy import deepcopy


class CentsField(m.IntegerField):
    """ Represents cents of currencies """
    pass


class PriceField(m.FloatField):

    min_value_validator = MinValueValidator(0, "Prices must be positive")

    def __init__(self, *args, **kwargs):
        validators = deepcopy(kwargs.pop('validators', []))
        if self.min_value_validator not in validators:
            validators.append(self.min_value_validator)
        return super().__init__(*args, **kwargs, validators=validators)


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
