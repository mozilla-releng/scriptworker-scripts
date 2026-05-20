import pytest
import referencing.exceptions

import build_decision.util.schema as schema


def test_remote_ref():
    """Ensure remote references aren't resolved."""
    remote_schema = schema.Schema({"$ref": "http://example.com"})
    with pytest.raises(referencing.exceptions.Unresolvable):
        remote_schema.validate("foo")
