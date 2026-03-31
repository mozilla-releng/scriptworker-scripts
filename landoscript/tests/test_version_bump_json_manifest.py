import json

import pytest
from mozilla_version.version import BaseVersion

from landoscript.actions.version_bump import apply_manifest_version_bump, parse_manifest_version


def _manifest(version):
    return json.dumps({"manifest_version": 2, "name": "New Tab", "version": version}, indent=2)


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
    "initial,next_v",
    [
        pytest.param("151.0.0", "151.1.0", id="normal_bump"),
        pytest.param("151.1.0", "151.2.0", id="subsequent_bump"),
    ],
)
def test_apply_manifest_version_bump(initial, next_v):
    orig = _manifest(initial)
    next_ = BaseVersion.parse(next_v)
    modified = apply_manifest_version_bump(orig, next_)
    assert f'"version": "{next_v}"' in modified
    assert f'"version": "{initial}"' not in modified


def test_apply_manifest_version_bump_does_not_touch_strict_min_version():
    orig = '{\n  "version": "151.0.0",\n  "browser_specific_settings": {"gecko": {"strict_min_version": "151.0.0"}}\n}'
    next_ = BaseVersion.parse("151.1.0")
    modified = apply_manifest_version_bump(orig, next_)
    assert '"version": "151.1.0"' in modified
    assert '"strict_min_version": "151.0.0"' in modified


def test_apply_manifest_version_bump_preserves_trailing_newline():
    orig = _manifest("151.0.0") + "\n"
    next_ = BaseVersion.parse("151.1.0")
    modified = apply_manifest_version_bump(orig, next_)
    assert modified.endswith("\n")
