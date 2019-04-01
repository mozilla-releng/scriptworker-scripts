import argparse
import pytest
import tempfile

from unittest.mock import MagicMock

from mozapkpublisher.common.apk import add_apk_checks_arguments, extract_and_check_apks_metadata


def test_add_apk_checks_arguments():
    parser = argparse.ArgumentParser()
    add_apk_checks_arguments(parser)

    with tempfile.NamedTemporaryFile('wb') as f:
        config = parser.parse_args([
            '--expected-package-name', 'some.package.name', f.name
        ])
        assert config.apks[0].name == f.name

    assert config.expected_package_names == ['some.package.name']


@pytest.mark.parametrize('expected_package_names, skip_check_package_names, raises', (
    ('some.package.name', False, False),
    ('', True, False),
    ('', False, True),
    ('some.package.name', True, True),
))
def test_extract_and_check_apks_metadata(monkeypatch, expected_package_names, skip_check_package_names, raises):
    monkeypatch.setattr(
        'mozapkpublisher.common.apk.extract_metadata',
        lambda _, __: {'some': 'metadata'}
    )
    monkeypatch.setattr(
        'mozapkpublisher.common.apk.cross_check_apks',
        lambda *args, **kwargs: None
    )

    apk_mock = MagicMock()
    apk_mock.name = '/some/path'
    apks = [apk_mock]

    if raises:
        with pytest.raises(ValueError):
            extract_and_check_apks_metadata(
                apks,
                expected_package_names,
                skip_check_package_names,
                True,
                True,
                True,
                True,
            )
    else:
        assert extract_and_check_apks_metadata(
            apks,
            expected_package_names,
            skip_check_package_names,
            True,
            True,
            True,
            True,
        ) == {'/some/path': {'some': 'metadata'}}
