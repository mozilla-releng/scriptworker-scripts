import json

import pytest

from landoscript.actions.version_bump import parse_manifest_version


def _manifest(version, name="New Tab"):
    return json.dumps({"manifest_version": 2, "name": name, "version": version}, indent=2)


@pytest.mark.parametrize(
    "version",
    ["151.0.0", "151.1.0", "151.2.0"],
)
def test_parse_manifest_version(version):
    result = parse_manifest_version(_manifest(version))
    assert str(result) == version


def test_parse_manifest_version_ignores_other_fields():
    contents = '{"manifest_version": 2, "version": "151.0.0", "strict_min_version": "140.0"}'
    result = parse_manifest_version(contents)
    assert str(result) == "151.0.0"


@pytest.mark.parametrize(
    "manifest_name",
    ["New Tab", "Web Compat"],
)
def test_parse_manifest_version_works_for_newtab_and_webcompat(manifest_name):
    result = parse_manifest_version(_manifest("151.0.0", name=manifest_name))
    assert str(result) == "151.0.0"
