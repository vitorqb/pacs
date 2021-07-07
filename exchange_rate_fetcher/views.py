from rest_framework.decorators import api_view
from rest_framework.response import Response

import exchange_rate_fetcher.serializers as serializers
import exchange_rate_fetcher.services as svc
import copy


TOKEN_HEADER = "HTTP_FETCH_CURRENCY_EXCHANGE_RATE_TOKEN"


class ExchangeRateDataViewSpec:

    @classmethod
    def get(cls, request):
        inputs = cls._serialize_inputs(request)
        fetch_svc = cls.get_service(inputs)
        data = fetch_svc.fetch(inputs.start_at, inputs.end_at,
                               inputs.currency_codes, 'USD', inputs.end_at)
        return Response(data)

    @staticmethod
    def _serialize_inputs(request):
        data = copy.deepcopy(request.query_params)
        token = request.META.get(TOKEN_HEADER, "")
        if token:
            data["token"] = token
        serializer = serializers.ExchangeRateDataInputsSerializer(data=data)
        serializer.is_valid(True)
        return serializer.save()

    @staticmethod
    def get_service(inputs):
        return svc.ExchangeRateFetcher(token=inputs.token)


data_view = api_view(['GET'])(ExchangeRateDataViewSpec.get)
