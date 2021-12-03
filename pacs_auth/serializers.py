import rest_framework.serializers as s
import common.serializers as cs
import pacs_auth.view_models as view_models


class PostApiKeySerializer(s.Serializer):
    admin_token = s.CharField()
    roles = cs.StringListField()

    def create(self, validated_data):
        return view_models.PostApiKeyViewModel(**validated_data)
