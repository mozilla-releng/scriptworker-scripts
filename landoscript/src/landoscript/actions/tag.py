from scriptworker.client import TaskVerificationError


async def run(tags):
    if len(tags) < 1:
        raise TaskVerificationError("must provide at least one tag!")

    actions = []
    for tag in tags:
        actions.append({"action": "tag", "name": tag})

    return actions
