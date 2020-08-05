import json

import pytest
import slugid
from click.testing import CliRunner

from configloader.script import main


@pytest.mark.parametrize(
    "input, env, exit_code, expected",
    (
        # basic case
        ({"a": "b"}, {}, 0, {"a": "b"}),
        # pod name
        (
            {"a": "b", "worker_id": "${WORKER_ID}"},
            {"K8S_POD_NAME": "worker"},
            0,
            {"a": "b", "worker_id": "worker"},
        ),
        # no pod name
        ({"a": "b", "worker_id": "${WORKER_ID}"}, {}, 0, {"a": "b", "worker_id": "abcdef"}),
        # long pod name
        (
            {"a": "b", "worker_id": "${WORKER_ID}"},
            {"K8S_POD_NAME": "worker-prefix-is-so-long-so-have-to-trim-it-down"},
            0,
            {"a": "b", "worker_id": "is-so-long-so-have-to-trim-it-down"},
        ),
        # environment variable is replaced
        (
            {"a": "b", "envvar": "${ENVVAR}"},
            {"ENVVAR": "replaced"},
            0,
            {"a": "b", "envvar": "replaced"},
        ),
        # fail on missing environment variables
        ({"a": "b", "envvar": "${ENVVAR}"}, {}, 1, {}),
    ),
)
def test_main(monkeypatch, input, env, exit_code, expected):
    runner = CliRunner()
    for envvar, envvalue in env.items():
        monkeypatch.setenv(envvar, envvalue)
    with runner.isolated_filesystem():
        with open("input.yml", "w") as input_file:
            json.dump(input, input_file)

        with monkeypatch.context() as m:
            m.setattr(slugid, "nice", lambda: "abcdef")
            result = runner.invoke(main, ["input.yml", "output.json"])
            assert result.exit_code == exit_code
            if exit_code == 0:
                output = json.load(open("output.json"))
                assert output == expected
