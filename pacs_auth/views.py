from rest_framework.decorators import api_view
from rest_framework.response import Response
from pacs_auth.models import Token


@api_view(["GET"])
def get_token(request):
    token_value = request.session.get("token_value")
    if not token_value:
        return Response(status=400)
    if not Token.objects.is_valid_token_value(token_value):
        return Response(status=400)
    return Response(data={"token_value": token_value}, status=200)
