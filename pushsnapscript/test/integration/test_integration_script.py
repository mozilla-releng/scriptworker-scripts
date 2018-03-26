import contextlib
import json
import os
import pytest
import tempfile

from scriptworker.utils import makedirs

from pushsnapscript.script import main
from pushsnapscript.snap_store import snapcraft_store_client

from scriptworker.test import event_loop
from pushsnapscript.test.test_snap_store import SNAPCRAFT_SAMPLE_CONFIG_BASE64, SNAPCRAFT_SAMPLE_CONFIG

assert event_loop   # silence flake8


@pytest.mark.parametrize('channel', ('candidate', 'edge'))
def test_script_can_push_snaps_with_credentials(event_loop, monkeypatch, channel):
    function_call_counter = (n for n in range(0, 2))

    config = {
        'base64_macaroons_configs': {
            'candidate': SNAPCRAFT_SAMPLE_CONFIG_BASE64,
            'edge': SNAPCRAFT_SAMPLE_CONFIG_BASE64,
        },
    }

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

            with tempfile.TemporaryDirectory() as temp_dir:
                def snapcraft_store_client_push_fake(snap_file_path, channel):
                    # This function can't be a regular mock because of the following check:
                    assert os.getcwd() == temp_dir     # Push must be done from a disposable dir

                    assert snap_file_path == snap_artifact_path
                    assert channel == channel
                    next(function_call_counter)

                @contextlib.contextmanager
                def TemporaryDirectory():
                    try:
                        yield temp_dir
                    finally:
                        pass

                monkeypatch.setattr(tempfile, 'TemporaryDirectory', TemporaryDirectory)
                monkeypatch.setattr(snapcraft_store_client, 'push', snapcraft_store_client_push_fake)
                main(config_path=config_file.name)

                snapcraft_cred_file = os.path.join(temp_dir, '.snapcraft', 'snapcraft.cfg')

                with open(os.path.join(snapcraft_cred_file)) as snapcraft_login_config:
                    assert snapcraft_login_config.read() == SNAPCRAFT_SAMPLE_CONFIG

    assert not os.path.exists(snapcraft_cred_file)
    assert next(function_call_counter) == 1     # Check fake function was called once
