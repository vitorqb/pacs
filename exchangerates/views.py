from rest_framework.decorators import api_view
from rest_framework.response import Response

from exchangerates.serializers import ExchangeRateDataInputsSerializer, PostExchangeRatesInputsSerializer
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
    serializer = PostExchangeRatesInputsSerializer(data=request.query_params)
    serializer.is_valid(True)
    input_data = serializer.save()
    options = services.ExchangeRateImportOptions(skip_existing=input_data.skip_existing)
    with open(request.FILES['exchangerates_csv'].temporary_file_path()) as f:
        rows = csv.DictReader(f, delimiter=POST_CSV_DELIMITER)
        exchangerates_inputs = [services.ExchangeRateImportInput.from_dict(row) for row in rows]
        services.import_exchangerates(exchangerates_inputs, options)
    return Response()
