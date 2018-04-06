import json
import os
import pytest
import tempfile

from scriptworker.utils import makedirs

from pushsnapscript.script import main
from pushsnapscript.snap_store import snapcraft_store_client

from scriptworker.test import event_loop

assert event_loop   # silence flake8


@pytest.mark.parametrize('channel', ('beta', 'candidate'))
def test_script_can_push_snaps_with_credentials(event_loop, monkeypatch, channel):
    push_call_counter = (n for n in range(0, 2))

    task = {
        'dependencies': ['some_snap_build_taskId'],
        'scopes': ['project:releng:snapcraft:firefox:{}'.format(channel)],
        'payload': {
            'upstreamArtifacts': [{
                'paths': [
                    'public/build/firefox-59.0.snap'
                ],
                'taskId': 'some_snap_build_taskId',
                'taskType': 'build'
            }],
        },
    }

    with tempfile.NamedTemporaryFile('w+') as macaroon_beta, \
            tempfile.NamedTemporaryFile('w+') as macaroon_candidate:
        config = {
            'macaroons_locations': {
                'candidate': macaroon_candidate.name,
                'beta': macaroon_beta.name,
            },
        }

        with tempfile.TemporaryDirectory() as work_dir:
            config['work_dir'] = work_dir

            with open(os.path.join(work_dir, 'task.json'), 'w') as task_file:
                json.dump(task, task_file)

            snap_artifact_dir = os.path.join(work_dir, 'cot/some_snap_build_taskId/public/build/')
            makedirs(snap_artifact_dir)
            snap_artifact_path = os.path.join(snap_artifact_dir, 'firefox-59.0.snap')
            with open(snap_artifact_path, 'w') as snap_file:
                snap_file.write(' ')

            # config_file is not put in the TemporaryDirectory() (like the others), because it usually lives
            # elsewhere on the filesystem
            with tempfile.NamedTemporaryFile('w+') as config_file:
                json.dump(config, config_file)
                config_file.seek(0)

                def snapcraft_store_client_push_fake(snap_file_path, channel):
                    assert snap_file_path == snap_artifact_path
                    assert channel == channel
                    next(push_call_counter)

                monkeypatch.setattr(snapcraft_store_client, 'push', snapcraft_store_client_push_fake)
                main(config_path=config_file.name)

    assert next(push_call_counter) == 1
