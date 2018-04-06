"""addonscript specific exceptions."""


class SignatureError(Exception):
    """Error when signed XPI is still missing or reported invalid by AMO."""

    pass
