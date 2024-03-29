"""pacs URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

import exchangerates.views
import featuretoggles.views
import pacs_auth.views
from accounts.views import AccountViewSet
from currencies.views import CurrencyViewSet
from movements.views import TransactionViewSet
from reports.views import balance_evolution_view, flow_evolution_view

urlpatterns = [
    path("admin/", admin.site.urls),
]

router = DefaultRouter()
router.register(r"accounts", AccountViewSet, "accounts")
router.register(r"currencies", CurrencyViewSet, "currencies")
router.register(r"transactions", TransactionViewSet, "transactions")

urlpatterns += router.urls

urlpatterns += [
    path(r"reports/flow-evolution/", flow_evolution_view),
    path(f"reports/balance-evolution/", balance_evolution_view),
    path(f"exchange_rates/data/v2", exchangerates.views.exchangerates),
    path(f"auth/token", pacs_auth.views.token_view),
    path(f"auth/api_key", pacs_auth.views.post_api_key),
    path(f"auth/test", pacs_auth.views.get_test),
    path(f"featuretoggles", featuretoggles.views.get_featuretoggles),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
