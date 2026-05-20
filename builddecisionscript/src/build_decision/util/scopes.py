# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.


def satisfies(*, have, require):
    """
    Return True if the scopes in "have" satisfy the scopes in "require".
    """
    assert isinstance(have, list)
    assert isinstance(require, list)
    for req_scope in require:
        for have_scope in have:
            if have_scope == req_scope or (
                have_scope.endswith("*") and req_scope.startswith(have_scope[:-1])
            ):
                break
        else:
            return False
    return True
