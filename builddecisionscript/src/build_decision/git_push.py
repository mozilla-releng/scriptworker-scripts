# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import json
import logging
import os

import slugid

from .decision import render_tc_yml

logger = logging.getLogger(__name__)


def build_decision(*, repository, dry_run):
    logging.info("Running build-decision task")

    payload = json.loads(os.environ["HOOK_PAYLOAD"])
    logger.info("Hook Payload:\n%s", json.dumps(payload, indent=4, sort_keys=True))

    event = {
        "after": payload["sha"],
        "base_ref": payload.get("base_ref"),
        "before": payload["base_sha"],
        "pusher": {"email": payload["owner"]},
        "ref": payload["ref"],
        "repository": {
            "name": repository.repo_path.split("/")[-1],
            "full_name": repository.repo_path,
            "html_url": repository.repo_url,
            "clone_url": repository.repo_url.rstrip("/") + ".git",
        },
    }

    tc_yml = repository.get_file(".taskcluster.yml", revision=event["after"])

    _slugids = {}

    def as_slugid(name):
        if name not in _slugids:
            _slugids[name] = slugid.nice()
        return _slugids[name]

    task = render_tc_yml(
        tc_yml,
        taskcluster_root_url=os.environ["TASKCLUSTER_ROOT_URL"],
        tasks_for="git-push",
        event=event,
        as_slugid=as_slugid,
    )

    task.display()
    if not dry_run:
        task.submit()
