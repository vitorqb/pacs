from common.testutils import PacsTestCase
from contextlib import contextmanager
from django.core.management import call_command
from exchangerates import models
import tempfile


@contextmanager
def temp_csv():
    with tempfile.NamedTemporaryFile() as f:
        f.writelines([
            b'date,currency_code,value',
            b'\n2021-10-15,EUR,1.1600',
            b'\n2021-10-14,EUR,1.1594',
            b'\n2021-10-15,BRL,0.1831',
            b'\n2021-10-14,BRL,0.1813',
        ])
        f.flush()
        yield f


class ImportExhcnageRateManagementCommandTest(PacsTestCase):

    def test_imports_four_rows(self):
        assert models.ExchangeRate.objects.all().count() == 0
        with temp_csv() as f:
            call_command('import_exchangerates', f.name)
        self.assertEqual(
            [
                x for x in models.ExchangeRate.objects.all()
            ],
            [
                models.ExchangeRate(1, "EUR", "2021-10-15", 1.16),
                models.ExchangeRate(2, "EUR", "2021-10-14", 1.594),
                models.ExchangeRate(3, "BRL", "2021-10-15", 0.1831),
                models.ExchangeRate(4, "BRL", "2021-10-14", 0.1813),
            ]
        )
