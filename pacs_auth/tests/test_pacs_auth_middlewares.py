from django.conf import settings

from rest_framework.test import APIRequestFactory
from django.core.exceptions import PermissionDenied

from unittest.mock import Mock

from common.test import PacsTestCase
from pacs_auth.middleware import PacsAuthMiddleware


class TestPacsAuthMiddleware(PacsTestCase):

    def setUp(self):
        super().setUp()
        self.request_factory = APIRequestFactory()
        self.middleware = PacsAuthMiddleware(Mock())

    def test_raises_403_if_token_is_not_present(self):
        request = self.request_factory.get('/accounts/')
        with self.assertRaises(PermissionDenied):
            self.middleware(request)

    def test_raises_403_if_token_is_incorrect(self):
        false_token = 1231123
        assert false_token != settings.ADMIN_TOKEN
        request = self.request_factory.get(
            '/accounts/',
            XAuthentication=f'Token {false_token}'
        )
        with self.assertRaises(PermissionDenied):
            self.middleware(request)

    def test_parses_request_if_token_is_set(self):
        request = self.request_factory.get(
            '/accounts/',
            HTTP_AUTHORIZATION=f'Token {settings.ADMIN_TOKEN}'
        )
        self.middleware(request)
        # No failed authentication!
