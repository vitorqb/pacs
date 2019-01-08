from django.conf import settings
from rest_framework.test import APIClient, APITestCase


class PacsTestCase(APITestCase):

    def setUp(self):
        super().setUp()
        self.client = APIClient(
            HTTP_AUTHORIZATION=f"Token {settings.ADMIN_TOKEN}"
        )
