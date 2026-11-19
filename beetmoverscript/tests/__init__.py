import jinja2

from beetmoverscript.utils import load_json


def noop_sync(*args, **kwargs):
    pass


async def noop_async(*args, **kwargs):
    pass


def get_fake_valid_config():
    config = {
        "release_schema_file": "src/beetmoverscript/data/release_beetmover_task_schema.json",
        "schema_file": "src/beetmoverscript/data/beetmover_task_schema.json",
        "maven_schema_file": "src/beetmoverscript/data/maven_beetmover_task_schema.json",
        "artifactMap_schema_file": "src/beetmoverscript/data/artifactMap_beetmover_task_schema.json",
        "upload_data_schema_file": "src/beetmoverscript/data/upload_data_task_schema.json",
    }
    config.update(load_json(path="tests/fake_config.json"))
    return config


def get_fake_valid_task(taskjson="task.json"):
    return load_json(path="tests/test_work_dir/{}".format(taskjson))


def get_fake_checksums_manifest():
    return (
        "14f2d1cb999a8b42a3b6b671f7376c3e246daa65d108e2b8fe880f069601dc2b26afa155b52001235db059 sha512 618149 firefox-53.0a1.en-US.linux-i686.complete.mar\n"
        "293975734953874539475 sha256 618149 firefox-53.0a1.en-US.linux-i686.complete.mar"
    )


def get_test_jinja_env():
    return jinja2.Environment(loader=jinja2.PackageLoader("tests"), undefined=jinja2.StrictUndefined)


PARTNER_PUSH_CANDIDATES_PREFIX = "pub/firefox/candidates/134.0-candidates/build2/"
PARTNER_PUSH_RELEASES_PREFIX = "pub/firefox/releases/134.0/"
PARTNER_PUSH_PARTNER_RELEASES_PREFIX = "pub/firefox/releases/partners/"
PARTNER_PUSH_CANDIDATES = (
    "linux-x86_64/en-US/firefox-134.0.tar.xz",
    "partner-repacks/p1/s1/v1/win64/en-US/setup.exe",
    "partner-repacks/p1/s1/v202501231439/win64/en-US/setup.exe",
    "partner-repacks/p1/s2/v1/win64/en-US/setup.exe",
    "partner-repacks/p1/s2/v10/win64/en-US/setup.exe",
    "partner-repacks/p2/s3/v1/win64/en-US/setup.exe",
)
# (partner_build_numbers payload field or None if absent, expected {source: destination} relative to the prefixes above, unmatched partners)
PARTNER_PUSH_CASES = (
    (
        None,
        {
            "linux-x86_64/en-US/firefox-134.0.tar.xz": "linux-x86_64/en-US/firefox-134.0.tar.xz",
            "partner-repacks/p1/s1/v1/win64/en-US/setup.exe": "p1/s1/134.0/win64/en-US/setup.exe",
            "partner-repacks/p1/s2/v1/win64/en-US/setup.exe": "p1/s2/134.0/win64/en-US/setup.exe",
        },
        [],
    ),
    (
        {"p1/s1": 202501231439},
        {
            "linux-x86_64/en-US/firefox-134.0.tar.xz": "linux-x86_64/en-US/firefox-134.0.tar.xz",
            "partner-repacks/p1/s1/v202501231439/win64/en-US/setup.exe": "p1/s1/134.0/win64/en-US/setup.exe",
            "partner-repacks/p1/s2/v1/win64/en-US/setup.exe": "p1/s2/134.0/win64/en-US/setup.exe",
        },
        [],
    ),
    (
        {"p1/s2": 10},
        {
            "linux-x86_64/en-US/firefox-134.0.tar.xz": "linux-x86_64/en-US/firefox-134.0.tar.xz",
            "partner-repacks/p1/s1/v1/win64/en-US/setup.exe": "p1/s1/134.0/win64/en-US/setup.exe",
            "partner-repacks/p1/s2/v10/win64/en-US/setup.exe": "p1/s2/134.0/win64/en-US/setup.exe",
        },
        [],
    ),
    (
        {"p1/s1": 202501231440},
        {
            "linux-x86_64/en-US/firefox-134.0.tar.xz": "linux-x86_64/en-US/firefox-134.0.tar.xz",
            "partner-repacks/p1/s2/v1/win64/en-US/setup.exe": "p1/s2/134.0/win64/en-US/setup.exe",
        },
        ["p1/s1"],
    ),
)


def get_partner_push_task(partner_build_numbers):
    payload = {"product": "firefox", "build_number": 2, "version": "134.0", "partners": ["p1/s1", "p1/s2"]}
    if partner_build_numbers is not None:
        payload["partner_build_numbers"] = partner_build_numbers
    return {"payload": payload}


def get_partner_push_expected_moves(expected):
    moves = {}
    for source, destination in expected.items():
        if source.startswith("partner-repacks/"):
            moves[PARTNER_PUSH_CANDIDATES_PREFIX + source] = PARTNER_PUSH_PARTNER_RELEASES_PREFIX + destination
        else:
            moves[PARTNER_PUSH_CANDIDATES_PREFIX + source] = PARTNER_PUSH_RELEASES_PREFIX + destination
    return moves
