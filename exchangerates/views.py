from rest_framework.decorators import api_view
from rest_framework.response import Response

from exchangerates.serializers import ExchangeRateDataInputsSerializer
import exchangerates.services as services

import csv


POST_CSV_DELIMITER = ','
POST_CSV_FILE_NAME = 'exchangerates_csv'


@api_view(["GET", "POST"])
def exchangerates(request, fetch_fn=services.fetch_exchange_rates):
    if request.method == 'GET':
        return get_exchangerates(request, fetch_fn)
    if request.method == 'POST':
        return post_exchangerates(request)
    raise NotImplementedError()


def get_exchangerates(request, fetch_fn):
    serializer = ExchangeRateDataInputsSerializer(data=request.query_params)
    serializer.is_valid(True)
    input_data = serializer.save()
    output_data = fetch_fn(start_at=input_data.start_at, end_at=input_data.end_at,
                           currency_codes=input_data.currency_codes)
    return Response(output_data)


def post_exchangerates(request):
    with open(request.FILES['exchangerates_csv'].temporary_file_path()) as f:
        for row in csv.DictReader(f, delimiter=POST_CSV_DELIMITER):
            exchangerate_import_input = services.ExchangeRateImportInput.from_dict(row)
            services.import_exchangerate(exchangerate_import_input)
    return Response()
