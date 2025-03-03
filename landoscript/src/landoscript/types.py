from typing import TypedDict

type Repo = str
type Branch = str
type Action = str


class VersionBumpInfo(TypedDict):
    pass


class Payload(TypedDict):
    actions: list[Action]
    repo: Repo
    branch: Branch
    version_bump_info: VersionBumpInfo


class Task(TypedDict):
    payload: Payload


# TODO: these should move to scriptworker or scriptworker_client
type Config = dict


# TODO: is this a dict or an object?
class Context(TypedDict):
    config: Config
    task: Task
