# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import, print_function, unicode_literals

import six

from taskgraph.target_tasks import _target_task, filter_for_tasks_for


def filter_for_script(task, parameters):
    return (
        parameters.get("script_name") is None or
        task.attributes.get("script-name") == parameters.get("script_name")
    )


@_target_task('default')
def target_tasks_default(full_task_graph, parameters, graph_config):
    """Filter by `run_on_tasks_for` and `script-name`."""
    return [l for l, t in six.iteritems(full_task_graph.tasks)
            if filter_for_tasks_for(t, parameters)
            and filter_for_script(t, parameters)]


@_target_task('docker-hub-push')
def target_tasks_default(full_task_graph, parameters, graph_config):
    """Filter by kind and `script-name`."""
    return [l for l, t in six.iteritems(full_task_graph.tasks)
            if t.kind == "k8s-image"
            and filter_for_script(t, parameters)]
