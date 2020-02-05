from rest_framework.decorators import api_view
from rest_framework.response import Response

import exchange_rate_fetcher.serializers as serializers
import exchange_rate_fetcher.services as svc


class ExchangeRateDataViewSpec:

    @classmethod
    def get(cls, request):
        inputs = cls._serialize_inputs(request)
        fetch_svc = cls.get_service()
        data = fetch_svc.fetch(inputs.start_at, inputs.end_at,
                               inputs.currency_codes, 'USD', inputs.end_at)
        return Response(data)

    @staticmethod
    def _serialize_inputs(request):
        data = request.query_params
        serializer = serializers.ExchangeRateDataInputsSerializer(data=data)
        serializer.is_valid(True)
        return serializer.save()

    @staticmethod
    def get_service():
        return svc.ExchangeRateFetcher()


data_view = api_view(['GET'])(ExchangeRateDataViewSpec.get)
