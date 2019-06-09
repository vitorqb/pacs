from __future__ import annotations

from typing import TYPE_CHECKING, List, Callable, Optional

from rest_framework.decorators import api_view
from rest_framework.response import Response

from currencies.currency_converter import CurrencyPricePortifolioConverter

from .reports import BalanceEvolutionQuery, FlowEvolutionQuery
from .serializers import (BalanceEvolutionInputSerializer,
                          BalanceEvolutionOutputSerializer,
                          FlowEvolutionInputSerializer,
                          FlowEvolutionOutputSerializer)
from .view_models import FlowEvolutionInput, CurrencyOpts

if TYPE_CHECKING:
    from reports.reports import AccountFlows
    from currencies.money import Money
    from datetime import date


# Balance evolution
def _balance_evolution_view(request):
    input_data = BalanceEvolutionInputSerializer(data=request.data).get_data()
    report = BalanceEvolutionQuery(**input_data).run()
    serialized_report = BalanceEvolutionOutputSerializer(report).data
    return Response(serialized_report)


balance_evolution_view = api_view(['POST'])(_balance_evolution_view)


# Flow evolution
class FlowEvolutionViewSpec:

    @staticmethod
    def _serialize_inputs(request) -> FlowEvolutionInput:
        serializer = FlowEvolutionInputSerializer(data=request.data)
        serializer.is_valid(True)
        return serializer.save()

    @classmethod
    def _run_query(cls, inputs: FlowEvolutionInput) -> List[AccountFlows]:
        currency_conversion_fn = cls._get_converter_fn(inputs.currency_opts)
        query = FlowEvolutionQuery(
            accounts=inputs.accounts,
            periods=inputs.periods,
            currency_conversion_fn=currency_conversion_fn,
        )
        return query.run()

    @staticmethod
    def _serialize_report(report: List[AccountFlows]):
        return FlowEvolutionOutputSerializer(report).data

    @classmethod
    def _get_converter_fn(
            cls,
            currency_opts: Optional[CurrencyOpts],
    ) -> Callable[[Money, date], Money]:
        if currency_opts is None:
            return lambda m, _: m
        dest_currency = currency_opts.convert_to
        converter = CurrencyPricePortifolioConverter(
            price_portifolio_list=currency_opts.price_portifolio
        )
        return lambda m, d: converter.convert(m, dest_currency, d)

    @classmethod
    def post(cls, request):
        inputs = cls._serialize_inputs(request)
        report = cls._run_query(inputs)
        serialized_report = cls._serialize_report(report)
        return Response(serialized_report)


flow_evolution_view = api_view(['POST'])(FlowEvolutionViewSpec.post)
