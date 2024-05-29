import json
import logging
import urllib

import certifi
import mohawk
import requests
from redo import retry

log = logging.getLogger(__name__)


class Release_V2(object):
    """A class that knows how to make requests to a Ship It v2 server,
    including generating hawk headers.
    """

    def __init__(self, taskcluster_client_id, taskcluster_access_token, api_root, ca_certs=certifi.where(), timeout=60, retry_attempts=5):
        self.taskcluster_client_id = taskcluster_client_id
        self.taskcluster_access_token = taskcluster_access_token
        self.api_root = api_root.rstrip("/")
        self.verify = ca_certs
        self.timeout = timeout
        self.retries = retry_attempts
        self.session = requests.session()

    @staticmethod
    def _get_taskcluster_headers(request_url, method, content, taskcluster_client_id, taskcluster_access_token):
        hawk = mohawk.Sender(
            {"id": taskcluster_client_id, "key": taskcluster_access_token, "algorithm": "sha256"}, request_url, method, content, content_type="application/json"
        )
        return {"Authorization": hawk.request_header, "Content-Type": "application/json"}

    def _request(self, api_endpoint, data=None, method="GET", headers={}):
        url = "{}{}".format(self.api_root, api_endpoint)
        headers = headers.copy()
        if method.upper() not in ("GET", "HEAD"):
            headers.update(self._get_taskcluster_headers(url, method, data, self.taskcluster_client_id, self.taskcluster_access_token))
        try:

            def _req():
                req = self.session.request(method=method, url=url, data=data, timeout=self.timeout, verify=self.verify, headers=headers)
                req.raise_for_status()
                return req

            return retry(_req, sleeptime=5, max_sleeptime=15, retry_exceptions=(requests.HTTPError, requests.ConnectionError), attempts=self.retries)
        except requests.HTTPError as err:
            log.error("Caught HTTPError: %d %s", err.response.status_code, err.response.content, exc_info=True)
            raise

    def getRelease(self, name, headers={}):
        resp = None
        try:
            resp = self._request(api_endpoint="/releases/{}".format(name), headers=headers)
            return json.loads(resp.content)
        except Exception:
            log.error("Caught error while getting release", exc_info=True)
            if resp:
                log.error(resp.content)
                log.error(f"Response code: {resp.status_code}")
            raise

    def get_releases(self, product, branch, status, version="", headers={}):
        """Method to map over the GET /releases List releases API in Ship-it"""
        resp = None
        params = {"product": product, "branch": branch, "status": status}
        if version:
            params["version"] = version

        try:
            resp = self._request(api_endpoint=f"/releases?{urllib.parse.urlencode(params)}", headers=headers)
            return resp.json()
        except Exception:
            log.error("Caught error while getting releases", exc_info=True)
            if resp:
                log.error(resp.content)
                log.error(f"Response code: {resp.status_code}")
            raise

    def update_status(self, name, status, headers={}):
        """Update release status"""
        data = json.dumps({"status": status})
        resp = self._request(api_endpoint="/releases/{}".format(name), method="PATCH", data=data, headers=headers).content
        return resp

    def get_disabled_products(self, headers={}):
        """Method to map over the GET /disabled-products/ API in Ship-it

        Returns which products are disabled for which branches
        {
          "devedition": [
            "releases/mozilla-beta",
            "projects/maple"
          ],
          "firefox": [
            "projects/maple",
            "try"
          ]
        }
        """
        resp = None
        try:
            resp = self._request(api_endpoint="/disabled-products", headers=headers)

            return resp.json()
        except Exception:
            log.error("Caught error while getting disabled-products", exc_info=True)
            if resp:
                log.error(resp.content)
                log.error(f"Response code: {resp.status_code}")
            raise

    def create_new_release(self, product, product_key, branch, version, build_number, revision, headers={}):
        """Method to map over the POST /releases/ API in Ship-it"""
        resp = None
        params = {"product": product, "branch": branch, "version": version, "build_number": build_number, "revision": revision, "partial_updates": "auto"}

        # some products such as Fennec take an additional argument to differentiate
        # between the flavors
        if product_key:
            params.update({"product_key": product_key})
        # guard the partials parameter to non-Fennec to prevent 400 BAD REQUEST
        if product == "fennec":
            del params["partial_updates"]
        data = json.dumps(params)

        try:
            resp = self._request(api_endpoint="/releases", method="POST", data=data, headers=headers)
            return resp.json()
        except Exception:
            log.error("Caught error while creating the release", exc_info=True)
            if resp:
                log.error(resp.content)
                log.error(f"Response code: {resp.status_code}")
            raise

    def trigger_release_phase(self, release_name, phase, headers={}):
        """Method to map over the PUT /releases/{name}/{phase} API in Ship-it

        Parameters:
            * release_name
            * phase
        """
        resp = None
        try:
            resp = self._request(api_endpoint=f"/releases/{release_name}/{phase}", method="PUT", data=None, headers=headers)
        except Exception:
            log.error(f"Caught error while triggering {phase} for {release_name}", exc_info=True)
            if resp:
                log.error(resp.content)
                log.error(f"Response code: {resp.status_code}")
            raise

    def get_product_channel_version(self, product, channel, headers=None):
        """Method to map over the GET /versions/{product}/{channel} API in Ship-it

        Parameters:
            * product
            * channel
        """
        headers = headers if headers else {}
        try:
            response = self._request(api_endpoint=f"/versions/{product}/{channel}", method="GET", headers=headers)
            return response.json()
        except Exception:
            log.error(f"Caught error while getting version for {product} {channel}!", exc_info=True)
            raise

    def update_product_channel_version(self, product, channel, version, headers=None):
        """Method to map over the PUT /versions/{product}/{channel} API in Ship-it

        Parameters:
            * product
            * channel
            * version
        """
        headers = headers if headers else {}
        data = json.dumps({"version": version})
        try:
            response = self._request(api_endpoint=f"/versions/{product}/{channel}", method="PUT", data=data, headers=headers)
            return response.json()
        except Exception:
            log.error(f"Caught error while getting version for {product} {channel}!", exc_info=True)
            raise
