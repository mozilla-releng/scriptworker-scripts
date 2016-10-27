import argparse
import pytest
import tempfile

from mozapkpublisher.googleplay import add_general_google_play_arguments


@pytest.mark.parametrize('package_name', [
    'org.mozilla.fennec_aurora', 'org.mozilla.firefox_beta', 'org.mozilla.firefox'
])
def test_add_general_google_play_arguments(package_name):
    parser = argparse.ArgumentParser()
    add_general_google_play_arguments(parser)

    with tempfile.NamedTemporaryFile('wb') as f:
        config = parser.parse_args([
            '--package-name', package_name, '--service-account', 'dummy@dummy', '--credentials', f.name
        ])
        assert config.google_play_credentials_file.name == f.name

    assert config.package_name == package_name
    assert config.service_account == 'dummy@dummy'


def test_add_general_google_play_arguments_wrong_package():
    parser = argparse.ArgumentParser()
    add_general_google_play_arguments(parser)

    with tempfile.NamedTemporaryFile('wb') as f:
        with pytest.raises(SystemExit) as e:
            parser.parse_args([
                '--package-name', 'wrong.package.name', '--service-account', 'dummy@dummy', '--credentials', f.name
            ])
