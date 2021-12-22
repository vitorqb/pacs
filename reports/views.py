from __future__ import annotations

from typing import TYPE_CHECKING, Callable, List, Optional

import attr
from rest_framework.decorators import api_view
from rest_framework.response import Response

from currencies.currency_converter import CurrencyPricePortifolioConverter

from .reports import BalanceEvolutionQuery, BalanceEvolutionReport, FlowEvolutionQuery
from .serializers import (
    BalanceEvolutionInputSerializer,
    BalanceEvolutionOutputSerializer,
    FlowEvolutionInputSerializer,
    FlowEvolutionOutputSerializer,
)
from .view_models import BalanceEvolutionInput, CurrencyOpts, FlowEvolutionInput

if TYPE_CHECKING:
    from datetime import date

    from currencies.money import Money
    from reports.reports import AccountFlows


# Balance evolution
class BalanceEvolutionViewSpec:
    @staticmethod
    def _serialize_inputs(request) -> BalanceEvolutionInput:
        serializer = BalanceEvolutionInputSerializer(data=request.data)
        serializer.is_valid(True)
        return serializer.save()

    @classmethod
    def _gen_report(cls, inputs: BalanceEvolutionInput) -> BalanceEvolutionReport:
        return BalanceEvolutionQuery(**inputs.as_dict()).run()

    @classmethod
    def post(cls, request):
        inputs = cls._serialize_inputs(request)
        report = cls._gen_report(inputs)
        data = BalanceEvolutionOutputSerializer(report).data
        return Response(data)


balance_evolution_view = api_view(["POST"])(BalanceEvolutionViewSpec.post)


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


flow_evolution_view = api_view(["POST"])(FlowEvolutionViewSpec.post)
