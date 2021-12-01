from rest_framework.decorators import api_view
from rest_framework.response import Response
from pacs_auth.models import Token, token_factory
from django.conf import settings


@api_view(["GET", "POST"])
def token_view(request):
    if request.method == 'POST':
        return post_token(request)
    if request.method == 'GET':
        return get_token(request)


def get_token(request):
    token_value = request.session.get("token_value")
    if not token_value:
        return Response(status=400)
    if not Token.objects.is_valid_token_value(token_value):
        return Response(status=400)
    return Response(data={"token_value": token_value}, status=200)


def post_token(request):
    if not request.data.get('admin_token') == settings.ADMIN_TOKEN:
        return Response(status=400)
    token = token_factory()
    request.session["token_value"] = token.value
    return Response(data={"token_value": token.value})


@api_view(["POST"])
def post_api_key(request):
    return Response()


@api_view(["GET"])
def get_test(request):
    return Response()
