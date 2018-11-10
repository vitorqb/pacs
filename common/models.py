import django.db.models as m


class CentsField(m.IntegerField):
    """ Represents cents of currencies """
    pass


class NameField(m.CharField):
    """ Fields for names """
    MAX_LENGTH = 150

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = self.MAX_LENGTH
        kwargs['unique'] = True
        super().__init__(*args, **kwargs)
