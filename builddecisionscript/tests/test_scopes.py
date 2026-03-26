# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import builddecisionscript.util.scopes as scopes
import pytest


@pytest.mark.parametrize(
    "have, require, expected",
    (
        (
            # We have a subset of required scopes.
            ["scope1", "scope2", "scope3"],
            ["scope1", "scope3"],
            True,
        ),
        (
            # We don't have all the required scopes.
            ["scope1", "scope2", "scope3"],
            ["scope1", "scope4"],
            False,
        ),
        (
            # We have all required scopes, matching against *
            ["prefix1/*", "prefix2/scope2", "prefix3/scope3-*"],
            ["prefix1/scope1", "prefix2/scope2", "prefix3/scope3-4"],
            True,
        ),
        (
            # We don't match against *
            ["prefix1/*", "prefix2/scope2", "prefix3/scope3-*"],
            ["prefix1/scope1", "prefix2/scope2-special", "prefix3/scope4-4"],
            False,
        ),
    ),
)
def test_satisfies(have, require, expected):
    """Add full coverage for ``scopes.satisfies``"""
    assert scopes.satisfies(have=have, require=require) == expected
