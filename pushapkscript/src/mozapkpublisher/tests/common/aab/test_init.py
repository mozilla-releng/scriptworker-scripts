import argparse
import tempfile

from mozapkpublisher.common.aab import add_aab_checks_arguments


def test_add_aab_checks_arguments():
    parser = argparse.ArgumentParser()
    add_aab_checks_arguments(parser)

    with tempfile.NamedTemporaryFile('wb') as f:
        config = parser.parse_args([f.name])
        assert config.aabs[0].name == f.name
