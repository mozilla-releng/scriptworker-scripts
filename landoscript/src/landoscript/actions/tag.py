from scriptworker.client import TaskVerificationError

from landoscript.lando import LandoAction


def run(tags: list[str], target_revision: str | None = None) -> list[LandoAction]:
    if len(tags) < 1:
        raise TaskVerificationError("must provide at least one tag!")

    actions = []
    for tag in tags:
        action = {"action": "tag", "name": tag}
        if target_revision:
            action["target"] = target_revision
        actions.append(action)

    return actions
