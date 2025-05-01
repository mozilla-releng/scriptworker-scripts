from dataclasses import dataclass

from aiohttp import ClientSession
from scriptworker.client import TaskVerificationError
from scriptworker.utils import retry_async

from landoscript.errors import LandoscriptError
from landoscript.lando import LandoAction


# We have two tag info classes to make it easy to signify whether the provided
# revision is an hg one or a git one. At the time of writing, we use the former
# for direct tagging tasks (such as `release-early-tagging`), and the latter
# for merge day operations, where the task payload does not contain a revision.
# When we switch all consumers (namely, Gecko) to firing their decision tasks
# off of Github events, we can drop `HgTagInfo`.
@dataclass(frozen=True)
class HgTagInfo:
    revision: str
    hg_repo_url: str
    tags: list[str]


@dataclass(frozen=True)
class GitTagInfo:
    revision: str
    tags: list[str]


async def run(session: ClientSession, tag_info: HgTagInfo | GitTagInfo) -> list[LandoAction]:
    if len(tag_info.tags) < 1:
        raise TaskVerificationError("must provide at least one tag!")

    git_commit = None
    if isinstance(tag_info, GitTagInfo):
        git_commit = tag_info.revision
    else:
        # tag_info.revision is an hg revision; lando wants a git revision
        resp = await retry_async(
            session.get,
            args=(f"{tag_info.hg_repo_url}/json-rev/{tag_info.revision}",),
            kwargs={"raise_for_status": True},
        )
        hg_revision_info = await resp.json()
        # TODO: figure out how to make this work on Try. At the moment, this
        # must be commented out because Try revisions don't have this metadata.
        if hg_revision_info.get("git_commit") is None:
            raise LandoscriptError("Couldn't look up target revision for tag(s) in hg, can't proceed!")
        git_commit = hg_revision_info["git_commit"]

    actions = []
    for tag in tag_info.tags:
        action = {"action": "tag", "name": tag}
        if git_commit:
            action["target"] = git_commit
        actions.append(action)

    return actions
