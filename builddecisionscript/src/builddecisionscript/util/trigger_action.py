# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

"""
Implement triggering actions.

For specification details see:
https://docs.taskcluster.net/docs/manual/design/conventions/actions/spec#action-context
"""

from __future__ import annotations

import json
import logging
import os

import attr
import jsone
import jsonschema

import taskcluster

from . import scopes
from .http import SESSION

logger = logging.getLogger(__name__)


def _is_task_in_context(context, task_tags):
    """
    A task (as defined by its tags) is said to match a tag-set if its
    tags are a super-set of the tag-set. A tag-set is a set of key-value pairs.

    An action (as defined by its context) is said to be relevant for
    a given task, if that task's tags match one of the tag-sets given
    in the context property for the action.
    """
    return any(all(tag in task_tags and task_tags[tag] == tag_set[tag] for tag in tag_set.keys()) for tag_set in context)


def _filter_relevant_actions(actions_json, original_task):
    """
    Each action entry (from action array) must define a name, title and description.
    The order of the array of actions is **significant**: actions should be displayed
    in this order, and when multiple actions apply, **the first takes precedence**.
    """
    relevant_actions = {}

    for action in actions_json["actions"]:
        action_name = action["name"]
        if action_name in relevant_actions:
            continue

        if original_task is None:
            if len(action["context"]) == 0:
                relevant_actions[action_name] = action
        else:
            if _is_task_in_context(action["context"], original_task.get("tags", {})):
                relevant_actions[action_name] = action

    return relevant_actions


def _check_decision_task_scopes(decision_task_id, hook_group_id, hook_id):
    queue = taskcluster.Queue(taskcluster.optionsFromEnvironment(), session=SESSION)
    auth = taskcluster.Auth(taskcluster.optionsFromEnvironment(), session=SESSION)
    decision_task = queue.task(decision_task_id)
    decision_task_scopes = auth.expandScopes({"scopes": decision_task["scopes"]})["scopes"]
    in_tree_scope = f"in-tree:hook-action:{hook_group_id}/{hook_id}"

    if not scopes.satisfies(have=decision_task_scopes, require=[in_tree_scope]):
        raise RuntimeError(
            "Action is misconfigured: "
            f"decision task's scopes do not include {in_tree_scope}\n"
            "Decision Task {decision_task_id} has scopes:\n" + "\n".join(f"  - {scope}" for scope in decision_task_scopes)
        )


def render_action(*, action_name, task_id, decision_task_id, action_input):
    queue = taskcluster.Queue(taskcluster.optionsFromEnvironment(), session=SESSION)

    logger.debug("Fetching actions.json...")
    actions_url = queue.buildUrl("getLatestArtifact", decision_task_id, "public/actions.json")
    actions_response = SESSION.get(actions_url)
    actions_response.raise_for_status()
    actions_json = actions_response.json()
    if task_id is not None:
        task_definition = queue.task(task_id)
    else:
        task_definition = None

    if actions_json["version"] != 1:
        raise RuntimeError("Wrong version of actions.json, unable to continue")

    relevant_actions = _filter_relevant_actions(actions_json, task_definition)

    if action_name not in relevant_actions:
        raise LookupError(f"{action_name} action is not available for this task. Available: {sorted(relevant_actions.keys())}")

    action = relevant_actions[action_name]

    if action["kind"] != "hook":
        raise NotImplementedError(f"Unable to submit actions with '{action['kind']}' kind.")

    _check_decision_task_scopes(
        decision_task_id,
        action["hookGroupId"],
        action["hookId"],
    )

    jsonschema.validate(action_input, action["schema"])

    context = {
        "taskGroupId": decision_task_id,
        "taskId": task_id or None,
        "input": action_input,
    }
    context.update(actions_json["variables"])

    hook_payload = jsone.render(action["hookPayload"], context)

    return Hook(
        hook_group_id=action["hookGroupId"],
        hook_id=action["hookId"],
        hook_payload=hook_payload,
    )


@attr.s(frozen=True)
class Hook:
    hook_group_id = attr.ib()
    hook_id = attr.ib()
    hook_payload = attr.ib()

    def display(self):
        logger.info(
            "Hook: %s/%s\nHook payload:\n%s",
            self.hook_group_id,
            self.hook_id,
            json.dumps(self.hook_payload, indent=4, sort_keys=True),
        )

    def submit(self):
        if "TASKCLUSTER_PROXY_URL" in os.environ:
            hooks = taskcluster.Hooks(
                {"rootUrl": os.environ["TASKCLUSTER_PROXY_URL"]},
                session=SESSION,
            )
        else:
            hooks = taskcluster.Hooks(taskcluster.optionsFromEnvironment(), session=SESSION)

        logger.info("Triggering hook %s/%s", self.hook_group_id, self.hook_id)
        result = hooks.triggerHook(self.hook_group_id, self.hook_id, self.hook_payload)
        logger.info("Task Id: %s", result["status"]["taskId"])
