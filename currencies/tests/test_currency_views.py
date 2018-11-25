from django.urls import resolve

from rest_framework.test import APIRequestFactory

from common.test import PacsTestCase
from .factories import CurrencyTestFactory
from currencies.views import CurrencyViewSet
from currencies.serializers import CurrencySerializer
from currencies.models import Currency


class CurrencyViewTestCase(PacsTestCase):

    def setUp(self):
        super().setUp()
        self.req_fact = APIRequestFactory()


class TestCurrencyView(CurrencyViewTestCase):

    def test_url_resolves_to_view_function(self):
        func = resolve('/currencies/').func
        assert func.cls == CurrencyViewSet

    def test_url_for_specific_currency_resolves_to_view(self):
        resolver = resolve('/currencies/1/')
        assert resolver.func.cls == CurrencyViewSet
        assert resolver.kwargs == {'pk': '1'}

    def test_get_currencies(self):
        curs = CurrencyTestFactory.create_batch(3)
        resp = self.client.get('/currencies/').json()
        assert [CurrencySerializer(x).data for x in curs] == resp

    def test_get_single_currency(self):
        cur = CurrencyTestFactory()
        resp = self.client.get(f'/currencies/{cur.pk}/').json()
        assert CurrencySerializer(cur).data == resp

    def test_post_single_currency(self):
        data = {'name': 'Yen'}
        resp = self.client.post('/currencies/', data).json()
        cur = Currency.objects.get(name="Yen")
        assert resp == CurrencySerializer(cur).data
