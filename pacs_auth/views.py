from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response

import pacs_auth.serializers as serializers
from pacs_auth.models import ApiKeyFactory, Token, token_factory


@api_view(["GET", "POST"])
def token_view(request):
    if request.method == "POST":
        return post_token(request)
    if request.method == "GET":
        return get_token(request)


def get_token(request):
    token_value = request.session.get("token_value")
    if not token_value:
        return Response(status=400)
    if not Token.objects.is_valid_token_value(token_value):
        return Response(status=400)
    return Response(data={"token_value": token_value}, status=200)


def post_token(request):
    if not request.data.get("admin_token") == settings.ADMIN_TOKEN:
        return Response(status=400)
    token = token_factory()
    request.session["token_value"] = token.value
    return Response(data={"token_value": token.value})


@api_view(["POST"])
def post_api_key(request):
    serializer = serializers.PostApiKeySerializer(data=request.data)
    serializer.is_valid(True)
    view_model = serializer.save()

    if not view_model.admin_token == settings.ADMIN_TOKEN:
        return Response(status=400)

    if len(view_model.roles) < 1:
        return Response(data={"error": "Missing roles!"}, status=400)

    api_key = ApiKeyFactory()(view_model.roles)
    return Response(data={"api_key": api_key.value})


@api_view(["GET"])
def get_test(request):
    return Response()
