import json
import os
import pytest
import tempfile

from distutils.util import strtobool

from mozapkpublisher.get_l10n_strings import GetL10nStrings
from mozapkpublisher.common.store_l10n import STORE_PRODUCT_DETAILS_PER_PACKAGE_NAME


@pytest.mark.skipif(strtobool(os.environ.get('SKIP_NETWORK_TESTS', 'true')), reason='Tests requiring network are skipped')
@pytest.mark.parametrize('package_name', STORE_PRODUCT_DETAILS_PER_PACKAGE_NAME.keys())
def test_download_files(package_name):
    with tempfile.NamedTemporaryFile('w+t', encoding='utf-8') as f:
        config = {
            'package_name': package_name,
            'output_file': f.name,
        }
        GetL10nStrings(config).run()

        f.seek(0)
        json.load(f)
        # TODO assert content is correct
