from balrogclient import Release


class V2Release(Release):
    url_template = "/v2/releases/%(name)s"
    prerequest_url_template = "/v2/releases/%(name)s"
