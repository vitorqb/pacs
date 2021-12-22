import argparse
import csv

from django.core.management import BaseCommand

import exchangerates.services as services

CSV_DELIMITER = ","


class Command(BaseCommand):

    help = """
      Imports exchange rates to the db from a `.csv` file.
      The file is expected to have the following format:

      ```
      date,currency_code,value
      2021-10-15,EUR,1.1600
      2021-10-14,EUR,1.1594
      2021-10-15,BRL,0.1831
      2021-10-14,BRL,0.1813
      ```

      where `value` is the value in dollars of the currency.
    """.strip()

    def add_arguments(self, parser):
        parser.add_argument("file", type=argparse.FileType("r"))

    def handle(self, *args, **options):
        for row in csv.DictReader(options["file"], delimiter=CSV_DELIMITER):
            exchangerate_import_input = services.ExchangeRateImportInput.from_dict(row)
            services.import_exchangerate(exchangerate_import_input)
