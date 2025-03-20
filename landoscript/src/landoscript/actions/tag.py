from scriptworker.client import TaskVerificationError

from landoscript.lando import LandoAction


def run(tags: list[str]) -> list[LandoAction]:
    if len(tags) < 1:
        raise TaskVerificationError("must provide at least one tag!")

    actions = []
    for tag in tags:
        actions.append({"action": "tag", "name": tag})

    return actions
