import json

import pytest
import slugid
from click.testing import CliRunner

from configloader.script import main


@pytest.mark.parametrize(
    "worker_id_prefix, input, env, exit_code, expected",
    (
        # basic case
        ("", {"a": "b"}, {}, 0, {"a": "b"}),
        # prefix
        (
            "workerPrefix",
            {"a": "b", "worker_id": "${WORKER_ID}"},
            {},
            0,
            {"a": "b", "worker_id": "workerPrefixabcdef"},
        ),
        # no prefix
        ("", {"a": "b", "worker_id": "${WORKER_ID}"}, {}, 0, {"a": "b", "worker_id": "abcdef"}),
        # long prefix
        (
            "workerPrefixIsSoLongSoSwHaveToTrimItDown",
            {"a": "b", "worker_id": "${WORKER_ID}"},
            {},
            0,
            {"a": "b", "worker_id": "workerPrefixIsSoLongSoSwHaveToTrimItDo"},
        ),
        # environment variable is replaced
        (
            "workerPrefix",
            {"a": "b", "envvar": "${ENVVAR}"},
            {"ENVVAR": "replaced"},
            0,
            {"a": "b", "envvar": "replaced"},
        ),
        # fail on missing environment variables
        ("workerPrefix", {"a": "b", "envvar": "${ENVVAR}"}, {}, 1, {}),
    ),
)
def test_main(monkeypatch, worker_id_prefix, input, env, exit_code, expected):
    runner = CliRunner()
    for envvar, envvalue in env.items():
        monkeypatch.setenv(envvar, envvalue)
    with runner.isolated_filesystem():
        with open("input.yml", "w") as input_file:
            json.dump(input, input_file)

        with monkeypatch.context() as m:
            m.setattr(slugid, "nice", lambda: "abcdef")
            result = runner.invoke(
                main, ["--worker-id-prefix", worker_id_prefix, "input.yml", "output.json"]
            )
            assert result.exit_code == exit_code
            if exit_code == 0:
                output = json.load(open("output.json"))
                assert output == expected
