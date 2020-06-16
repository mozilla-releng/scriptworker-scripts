# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import, print_function, unicode_literals

from taskgraph.parameters import extend_parameters_schema
from voluptuous import (
    Any,
    Optional,
    Required,
)

PROJECT_SPECIFIC_PREFIXES = ("refs/heads/dev-", "refs/heads/production-")

scriptworker_schema = {
    Optional('script_name'): Any(basestring, None),
    Optional('script_revision'): Any(basestring, None),
    Optional('shipping_phase'): Any("build", "promote", None),
}

extend_parameters_schema(scriptworker_schema)


def get_decision_parameters(graph_config, parameters):
    """Add repo-specific decision parameters.

    If we're on a production- or dev- branch, detect and set the `script_name`.

    """
    for prefix in PROJECT_SPECIFIC_PREFIXES:
        if parameters["head_ref"].startswith(prefix):
            parameters["script_name"] = parameters["head_ref"].replace(prefix, "")