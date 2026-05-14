# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


from typing import Literal, Optional

from taskgraph.parameters import extend_parameters_schema
from taskgraph.util.schema import Schema

PROJECT_SPECIFIC_PREFIXES = {
    "refs/heads/dev-": "dev",
    "refs/heads/production-": "production",
}

PUSH_TAGS = ("dev", "production")


def get_defaults(_):
    return {
        "docker_tag": None,
        "script_name": None,
        "script_revision": None,
        "shipping_phase": None,
    }


ScriptworkerSchema = Schema.from_dict(
    {
        "docker_tag": Optional[str],
        "script_name": Optional[str],
        "script_revision": Optional[str],
        "shipping_phase": Optional[Literal["build", "promote"]],
    },
    name="ScriptworkerSchema",
)

extend_parameters_schema(ScriptworkerSchema, defaults_fn=get_defaults)


def get_decision_parameters(graph_config, parameters):
    """Add repo-specific decision parameters.

    If we're on a production- or dev- branch, detect and set the `script_name`.

    """
    if parameters["tasks_for"] == "github-pull-request":
        parameters["docker_tag"] = "github-pull-request"
    elif parameters["head_ref"].startswith("refs/heads/"):
        parameters["docker_tag"] = parameters["head_ref"].replace("refs/heads/", "")
        for prefix, tag in PROJECT_SPECIFIC_PREFIXES.items():
            if parameters["head_ref"].startswith(prefix):
                parameters["script_name"] = parameters["head_ref"].replace(prefix, "")
                parameters["docker_tag"] = tag
                break
        if parameters["docker_tag"] in PUSH_TAGS and parameters["level"] == "3":
            parameters["optimize_target_tasks"] = False
