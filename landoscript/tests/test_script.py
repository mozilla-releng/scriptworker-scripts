import os.path
import pytest
import tempfile

from landoscript.script import async_main


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload,version_files,expected_bumps",
    (
        pytest.param(
            {
                "actions": ["version_bump"],
                "repo": "fake_repo",
                "branch": "fake_branch",
                "version_bump_info": {
                    "files": ["version.txt"],
                    "next_version": "135.0",
                },
            },
            {
                "version.txt": "134.0",
            },
            ["version.txt"],
            id="one_file_new_version",
        ),
    ),
    # minor bump
    # one file unchanged version
    # many files all changed
    # many files some changed
    # dontbuild flag includes correct commit message
)
async def test_version_bump(aioresponses, config, payload, version_files, expected_bumps):
    repo = payload["repo"]
    branch = payload["branch"]

    aioresponses.post(f"{config['lando_api']}/api/v1/{repo}/{branch}")

    with tempfile.TemporaryDirectory() as tmpd:
        for file, contents in version_files.items():
            with open(os.path.join(tmpd, file), "w+") as f:
                f.write(contents)

        task = {"payload": payload}
        await async_main(config, task)

    # expect a request to lando with a new version and maybe other things in the payload
    # you should be able to inspect the requests with something on `aioresponses`
    import pdb

    pdb.set_trace()


# tsets for each action on their own
# tests for combinations of actions
