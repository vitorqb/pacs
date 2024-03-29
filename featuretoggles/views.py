from rest_framework.decorators import api_view
from rest_framework.response import Response

import featuretoggles.services as services


@api_view(["GET"])
def get_featuretoggles(request):
    return Response(services.get_instance().get_dict())
