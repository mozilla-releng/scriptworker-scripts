import argparse
import tempfile

from mozapkpublisher.common.apk import add_apk_checks_arguments


def test_add_apk_checks_arguments():
    parser = argparse.ArgumentParser()
    add_apk_checks_arguments(parser)

    with tempfile.NamedTemporaryFile('wb') as f:
        config = parser.parse_args([
            '--expected-package-name', 'some.package.name', f.name
        ])
        assert config.apks[0].name == f.name

    assert config.expected_package_names == ['some.package.name']
