import json
import logging
import urllib

import certifi
import mohawk
import requests
from redo import retry

log = logging.getLogger(__name__)


class Release_V2(object):
    """A class that knows how to make requests to a Ship It v2 server, including
    generating hawk headers.
    """

    def __init__(
        self,
        taskcluster_client_id,
        taskcluster_access_token,
        api_root,
        ca_certs=certifi.where(),
        timeout=60,
        retry_attempts=5,
    ):
        self.taskcluster_client_id = taskcluster_client_id
        self.taskcluster_access_token = taskcluster_access_token
        self.api_root = api_root.rstrip('/')
        self.verify = ca_certs
        self.timeout = timeout
        self.retries = retry_attempts
        self.session = requests.session()

    @staticmethod
    def _get_taskcluster_headers(
        request_url, method, content, taskcluster_client_id, taskcluster_access_token
    ):
        hawk = mohawk.Sender(
            {
                'id': taskcluster_client_id,
                'key': taskcluster_access_token,
                'algorithm': 'sha256',
            },
            request_url,
            method,
            content,
            content_type='application/json',
        )
        return {
            'Authorization': hawk.request_header,
            'Content-Type': 'application/json',
        }

    def _request(self, api_endpoint, data=None, method='GET', headers={}):
        url = '{}{}'.format(self.api_root, api_endpoint)
        if method.upper() not in ('GET', 'HEAD'):
            headers.update(
                self._get_taskcluster_headers(
                    url,
                    method,
                    data,
                    self.taskcluster_client_id,
                    self.taskcluster_access_token,
                )
            )
        try:

            def _req():
                req = self.session.request(
                    method=method,
                    url=url,
                    data=data,
                    timeout=self.timeout,
                    verify=self.verify,
                    headers=headers,
                )
                req.raise_for_status()
                return req

            return retry(
                _req,
                sleeptime=5,
                max_sleeptime=15,
                retry_exceptions=(requests.HTTPError, requests.ConnectionError),
                attempts=self.retries,
            )
        except requests.HTTPError as err:
            log.error(
                'Caught HTTPError: %d %s',
                err.response.status_code,
                err.response.content,
                exc_info=True,
            )
            raise

    def getRelease(self, name, headers={}):
        resp = None
        try:
            resp = self._request(
                api_endpoint='/releases/{}'.format(name), headers=headers
            )
            return json.loads(resp.content)
        except Exception:
            log.error('Caught error while getting release', exc_info=True)
            if resp:
                log.error(resp.content)
                log.error('Response code: %d', resp.status_code)
            raise

    def get_shipped_releases(self, product, branch, headers={}):
        """Method to map over the GET /releases List releases API in Ship-it

        Parameters:
            * product
            * branch

        Returns a list of objects describing the releases:
        [
	  {
	    "allow_phase_skipping": false,
	    "branch": "releases/mozilla-beta",
	    "build_number": 1,
	    "completed": "2019-02-19T16:44:51.756118Z",
	    "created": "2019-02-18T16:57:47.612283Z",
	    "name": "Firefox-66.0b9-build1",
	    "phases": [
	      {
		"actionTaskId": "Z3xdvohqSImzFpx1wmIwGg",
		"completed": "2019-02-18T16:59:33.753914Z",
		"created": "2019-02-18T16:57:47.616646Z",
		"name": "promote_firefox",
		"skipped": false,
		"submitted": true
	      },
	      {
		"actionTaskId": "EOh-CPdgQfKTiMDqKRD3DQ",
		"completed": "2019-02-18T21:29:25.381553Z",
		"created": "2019-02-18T16:57:47.619101Z",
		"name": "push_firefox",
		"skipped": false,
		"submitted": true
	      },
	      {
		"actionTaskId": "eB7BsOEBQnOkPWKvLEkG7g",
		"completed": "2019-02-19T16:44:51.756118Z",
		"created": "2019-02-18T16:57:47.620507Z",
		"name": "ship_firefox",
		"skipped": false,
		"submitted": true
	      }
	    ],
	    "product": "firefox",
	    "project": "mozilla-beta",
	    "release_eta": "",
	    "revision": "bce0092f646c52d0402531a5b5a860905dfe7ad8",
	    "status": "shipped",
	    "version": "66.0b9"
	  },
          ...
        ]
        """
        resp = None
        most_recent_params = {
            'product': product,
            'branch': branch,
            'status': 'shipped'
        }
        try:
            resp = self._request(
                api_endpoint=f'/releases?{urllib.parse.urlencode(most_recent_params)}',
                headers=headers
            )
            return resp.json()
        except Exception:
            log.error('Caught error while getting releases', exc_info=True)
            if resp:
                log.error(resp.content)
                log.error('Response code: %d', resp.status_code)
            raise

    def update_status(self, name, status, rebuild_product_details=True, headers={}):
        """Update release status"""
        data = json.dumps({'status': status})
        res = self._request(
            api_endpoint='/releases/{}'.format(name),
            method='PATCH',
            data=data,
            headers=headers,
        ).content
        if rebuild_product_details:
            self._request(
                api_endpoint='/product-details',
                method='POST',
                data='{}',
                headers=headers,
            )
        return res

    def releases_are_disabled(self, product, channel, headers={}):
        pass

    def get_next_release_version(self, product, channel, headers={}):
        pass

    def get_most_recent_shipped_revision(self, product, channel, headers={}):
        pass

    def create_new_release(
        self, product, repo, channel, release_name, version, revision, headers={}
    ):
        if self.releases_are_disabled(product, channel):
            return
        pass

    def trigger_release_phase(self, product, channel, release_name, phase, headers={}):
        """Trigger a push phase for a specific release"""
        if self.releases_are_disabled(product, channel):
            return

        self._request(
            api_endpoint='/releases/{}/{}'.format(release_name, phase),
            method='PUT',
            data=None,
            headers=headers,
        )
