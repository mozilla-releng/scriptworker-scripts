# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import pytest
from builddecisionscript.task import validate_task_schema


def test_validate_hg_push_task(hg_push_task):
    validate_task_schema(hg_push_task)


def test_validate_cron_task(cron_task):
    validate_task_schema(cron_task)


def test_validate_cron_task_with_optional_fields(cron_task):
    cron_task["payload"]["branch"] = "beta"
    cron_task["payload"]["forceRun"] = "nightly"
    cron_task["payload"]["cronInput"] = {"key": "value"}
    cron_task["payload"]["dryRun"] = True
    validate_task_schema(cron_task)


def test_validate_hg_push_task_with_taskcluster_yml_repo(hg_push_task):
    hg_push_task["payload"]["taskclusterYmlRepo"] = "https://hg.mozilla.org/other-repo"
    validate_task_schema(hg_push_task)


def test_validate_missing_required_field():
    task = {
        "payload": {
            "command": "hg-push",
            "repoUrl": "https://hg.mozilla.org/mozilla-central",
            # missing project, level, repositoryType, trustDomain
        }
    }
    with pytest.raises(ValueError, match="Invalid task payload"):
        validate_task_schema(task)


def test_validate_invalid_command():
    task = {
        "payload": {
            "command": "unknown",
            "repoUrl": "https://hg.mozilla.org/mozilla-central",
            "project": "mozilla-central",
            "level": "3",
            "repositoryType": "hg",
            "trustDomain": "gecko",
        }
    }
    with pytest.raises(ValueError, match="Invalid task payload"):
        validate_task_schema(task)


def test_validate_invalid_repository_type():
    task = {
        "payload": {
            "command": "hg-push",
            "repoUrl": "https://hg.mozilla.org/mozilla-central",
            "project": "mozilla-central",
            "level": "3",
            "repositoryType": "svn",
            "trustDomain": "gecko",
        }
    }
    with pytest.raises(ValueError, match="Invalid task payload"):
        validate_task_schema(task)
