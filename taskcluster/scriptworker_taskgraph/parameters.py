# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


from taskgraph.parameters import extend_parameters_schema
from voluptuous import (
    Any,
    Optional,
    Required,
)

PROJECT_SPECIFIC_PREFIXES = {
    "refs/heads/dev-": "dev",
    "refs/heads/production-": "production",
}

PUSH_TAGS = ("dev", "production")

scriptworker_schema = {
    Optional('docker_tag'): Any(str, None),
    Optional('push_docker_image'): Any(True, False, None),
    Optional('script_name'): Any(str, None),
    Optional('script_revision'): Any(str, None),
    Optional('shipping_phase'): Any("build", "promote", None),
}

extend_parameters_schema(scriptworker_schema)


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
                parameters["docker_tag" ] = tag
                break
        if parameters["docker_tag"] in PUSH_TAGS and parameters["level"] == "3":
            parameters["push_docker_image"] = True
            parameters["optimize_target_tasks"] = False
            parameters["target_tasks_method"] = "docker-hub-push"
