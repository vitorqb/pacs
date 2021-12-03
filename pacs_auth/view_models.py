import attr


@attr.s(frozen=True)
class PostApiKeyViewModel:
    admin_token = attr.ib()
    roles = attr.ib()
