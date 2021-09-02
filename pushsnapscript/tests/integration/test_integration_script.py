import json
import os
import tempfile
from unittest.mock import MagicMock

import pytest
from scriptworker.utils import makedirs

from pushsnapscript import snap_store
from pushsnapscript.script import main

_ALL_REVISIONS_ABSTRACT = [
    {
        "series": ["16"],
        "channels": ["beta"],
        "version": "63.0b9-1",
        "timestamp": "2018-09-25T03:06:29Z",
        "current_channels": [],
        "release_map": [],
        "arch": "amd64",
        "revision": 134,
    },
    {
        "series": ["16"],
        "channels": ["candidate", "stable"],
        "version": "62.0.2-1",
        "timestamp": "2018-09-21T14:09:42Z",
        "current_channels": [],
        "release_map": [],
        "arch": "amd64",
        "revision": 133,
    },
    {
        "series": ["16"],
        "channels": ["esr/stable"],
        "version": "60.2.1esr-1",
        "timestamp": "2018-09-21T13:37:29Z",
        "current_channels": ["esr/stable", "esr/candidate", "esr/beta", "esr/edge"],
        "release_map": [
            {"series": "16", "architecture": "amd64", "channel": "esr/stable"},
            {"series": "16", "architecture": "amd64", "channel": "esr/candidate"},
            {"series": "16", "architecture": "amd64", "channel": "esr/beta"},
            {"series": "16", "architecture": "amd64", "channel": "esr/edge"},
        ],
        "arch": "amd64",
        "revision": 132,
    },
    {
        "series": ["16"],
        "channels": ["beta"],
        "version": "63.0b8-1",
        "timestamp": "2018-09-21T13:04:41Z",
        "current_channels": ["beta", "edge"],
        "release_map": [{"series": "16", "architecture": "amd64", "channel": "beta"}, {"series": "16", "architecture": "amd64", "channel": "edge"}],
        "arch": "amd64",
        "revision": 131,
    },
    {
        "series": ["16"],
        "channels": ["beta"],
        "version": "63.0b7-1",
        "timestamp": "2018-09-18T01:48:33Z",
        "current_channels": [],
        "release_map": [],
        "arch": "amd64",
        "revision": 130,
    },
    {
        "series": ["16"],
        "channels": ["candidate", "stable"],
        "version": "62.0-2",
        "timestamp": "2018-09-04T09:09:32Z",
        "current_channels": ["stable", "candidate"],
        "release_map": [{"series": "16", "architecture": "amd64", "channel": "stable"}, {"series": "16", "architecture": "amd64", "channel": "candidate"}],
        "arch": "amd64",
        "revision": 124,
    },
]


@pytest.mark.parametrize("channel, expected_revision", (("beta", 134), ("candidate", 133)))
def test_script_can_push_snaps_with_credentials(monkeypatch, channel, expected_revision):
    task = {
        "dependencies": ["some_snap_build_taskId"],
        "scopes": ["project:releng:snapcraft:firefox:{}".format(channel)],
        "payload": {
            "channel": channel,
            "upstreamArtifacts": [{"paths": ["public/build/target.snap"], "taskId": "some_snap_build_taskId", "taskType": "build"}],
        },
    }

    snapcraft_store_client_mock = MagicMock()
    store_mock = MagicMock()
    store_mock.get_snap_revisions.return_value = _ALL_REVISIONS_ABSTRACT

    def cpi_get_side_effect(*args, **kwargs):
        revision = kwargs["params"]["revision"]
        cpi_get_mock = MagicMock()
        cpi_get_mock.json.return_value = {"download_sha3_384": "fake_hash_rev{}".format(revision)}
        return cpi_get_mock

    store_mock.cpi.get.side_effect = cpi_get_side_effect

    monkeypatch.setattr(snap_store, "StoreClient", lambda: store_mock)
    monkeypatch.setattr(snap_store, "get_hash", lambda *args, **kwargs: "fake_hash_rev{}".format(expected_revision))

    with tempfile.NamedTemporaryFile("w+") as macaroon_beta, tempfile.NamedTemporaryFile("w+") as macaroon_candidate:
        config = {"push_to_store": True, "macaroons_locations": {"candidate": macaroon_candidate.name, "beta": macaroon_beta.name}}

        with tempfile.TemporaryDirectory() as work_dir:
            config["work_dir"] = work_dir

            with open(os.path.join(work_dir, "task.json"), "w") as task_file:
                json.dump(task, task_file)

            snap_artifact_dir = os.path.join(work_dir, "cot/some_snap_build_taskId/public/build/")
            makedirs(snap_artifact_dir)
            snap_artifact_path = os.path.join(snap_artifact_dir, "target.snap")
            with open(snap_artifact_path, "w") as snap_file:
                snap_file.write(" ")

            # config_file is not put in the TemporaryDirectory() (like the others), because it usually lives
            # elsewhere on the filesystem
            with tempfile.NamedTemporaryFile("w+") as config_file:
                json.dump(config, config_file)
                config_file.seek(0)

                monkeypatch.setattr(snap_store, "snapcraft_store_client", snapcraft_store_client_mock)
                main(config_path=config_file.name)

    snapcraft_store_client_mock.push.assert_called_once_with(snap_filename=snap_artifact_path)
    store_mock.release.assert_not_called()
