from rest_framework.decorators import api_view
from rest_framework.response import Response

from .reports import BalanceEvolutionQuery
from .serializers import (BalanceEvolutionInputSerializer,
                          BalanceEvolutionOutputSerializer)


def _balance_evolution_view(request):
    input_data = BalanceEvolutionInputSerializer(data=request.data).get_data()
    report = BalanceEvolutionQuery(**input_data).run()
    serialized_report = BalanceEvolutionOutputSerializer(report).data
    return Response(serialized_report)


balance_evolution_view = api_view(['POST'])(_balance_evolution_view)
