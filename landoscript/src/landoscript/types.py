from typing import TypedDict

from landoscript.github import GithubConfig

SourceRepo = str
Branch = str
Action = str
Version = str
Filename = str


class VersionBumpInfo(TypedDict):
    next_version: Version
    files: list[Filename]


class Payload(TypedDict):
    actions: list[Action]
    source_repo: SourceRepo
    branch: Branch
    version_bump_info: VersionBumpInfo
    dontbuild: bool
    ignore_closed_tree: bool


class Task(TypedDict):
    payload: Payload


# TODO: these should move to scriptworker_client
class LandoscriptConfig(TypedDict):
    lando_api: str
    work_dir: str
    artifact_dir: str
    schema_file: str
    github_config: GithubConfig


class Context(object):
    config: LandoscriptConfig
    task: Task
