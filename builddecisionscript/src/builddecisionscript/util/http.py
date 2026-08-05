# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

SESSION = requests.Session()
adapter = HTTPAdapter(
    max_retries=Retry(
        total=3,
        read=3,
        connect=3,
        backoff_factor=0.3,
        status_forcelist=(500, 502, 503, 504),
    )
)
SESSION.mount("http://", adapter)
SESSION.mount("https://", adapter)
