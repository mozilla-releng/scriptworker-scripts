from scriptworker.client import TaskVerificationError


def run(tags, target_revision=None):
    if len(tags) < 1:
        raise TaskVerificationError("must provide at least one tag!")

    actions = []
    for tag in tags:
        action = {"action": "tag", "name": tag}
        if target_revision:
            action["target"] = target_revision
        actions.append(action)

    return actions
