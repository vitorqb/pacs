from rest_framework.decorators import api_view
from rest_framework.response import Response

from exchangerates.serializers import ExchangeRateDataInputsSerializer
from exchangerates.services import fetch_exchange_rates


@api_view(['GET'])
def get_exchangerates(request, fetch_fn=fetch_exchange_rates):
    serializer = ExchangeRateDataInputsSerializer(data=request.query_params)
    serializer.is_valid(True)
    input_data = serializer.save()
    output_data = fetch_fn(start_at=input_data.start_at, end_at=input_data.end_at,
                           currency_codes=input_data.currency_codes)
    return Response(output_data)
