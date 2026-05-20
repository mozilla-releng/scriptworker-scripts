# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import attr
import yaml
from jsonschema.validators import validator_for
from referencing import Registry


def _get_validator(schema):
    # jsonschema by default allows remote references in the schema, so we
    # override its default registry with one that does not do that.
    registry = Registry()
    cls = validator_for(schema)
    cls.check_schema(schema)
    return cls(schema, registry=registry)


@attr.s(frozen=True)
class Schema:
    _schema = attr.ib()
    _validator = attr.ib(
        init=False,
        default=attr.Factory(
            lambda self: _get_validator(self._schema), takes_self=True
        ),
    )

    @classmethod
    def from_file(cls, path):
        schema = yaml.safe_load(path.read_text())
        return cls(schema)

    def validate(self, value):
        self._validator.validate(value)
