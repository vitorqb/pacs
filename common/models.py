import django.db.models as m
from django.core.validators import MinValueValidator


class CentsField(m.IntegerField):
    """ Represents cents of currencies """
    pass


class CentsPriceField(CentsField):
    def __init__(self, *args, **kwargs):
        if 'validators' not in kwargs:
            kwargs['validators'] = []
        kwargs['validators'].append(MinValueValidator(1, "Prices must be positive"))
        return super().__init__(*args, **kwargs)


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
