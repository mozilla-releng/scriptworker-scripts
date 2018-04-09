"""addonscript specific exceptions."""


class SignatureError(Exception):
    """Error when signed XPI is still missing or reported invalid by AMO."""

    pass


class AMOConflictError(Exception):
    """Error when AMO returns 409-Conflict usually from a duplicate version."""

    pass
