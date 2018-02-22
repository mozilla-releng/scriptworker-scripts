import json
import logging
# import base64
# import httplib
# import socket
# import sys
# import traceback
# import urllib
# import urllib2
from xml.dom.minidom import parseString
from six.moves.urllib.parse import quote

# from mozharness.base.log import FATAL


log = logging.getLogger(__name__)


def load_json(path):
    with open(path, "r") as fh:
        return json.load(fh)


async def api_call(context, route, data, error_level='fatal', retry_config=None):
    """TODO"""
    retry_async_kwargs = dict(
        failure_status=None,
        retry_exceptions=(urllib2.HTTPError, urllib2.URLError,
                          httplib.BadStatusLine,
                          socket.timeout, socket.error),
        error_message="call to %s failed" % (route),
        error_level=error_level,
    )

    if retry_config:
        retry_async_kwargs.update(retry_config)

    await retry_async(_api_call, args=(route, data),
                      retry_exceptions=(Exception, ),
                      **retry_async_kwargs)

async def _api_call(context, route, data):
    """TODO"""
    bouncer_config = context.config["bouncer_config"][context.server]
    credentials = (bouncer_config["username"],
                   bouncer_config["password"])
    api_root = bouncer_config["api_root"]
    api_url = "%s/%s" % (api_root, route)

    request = urllib2.Request(api_url)
    if data:
        post_data = urllib.urlencode(data, doseq=True)
        request.add_data(post_data)
        self.info("POST data: %s" % post_data)
    if credentials:
        auth = base64.encodestring('%s:%s' % credentials)
        request.add_header("Authorization", "Basic %s" % auth.strip())
    try:
        self.info("Submitting to %s" % api_url)
        res = urllib2.urlopen(request, timeout=60).read()
        self.info("Server response")
        self.info(res)
        return res
    except urllib2.HTTPError as e:
        self.warning("Cannot access %s" % api_url)
        traceback.print_exc(file=sys.stdout)
        self.warning("Returned page source:")
        self.warning(e.read())
        raise
    except urllib2.URLError:
        traceback.print_exc(file=sys.stdout)
        self.warning("Cannot access %s" % api_url)
        raise
    except socket.timeout as e:
        self.warning("Timed out accessing %s: %s" % (api_url, e))
        raise
    except socket.error as e:
        self.warning("Socket error when accessing %s: %s" % (api_url, e))
        raise
    except httplib.BadStatusLine as e:
        self.warning('BadStatusLine accessing %s: %s' % (api_url, e))
        raise


async def product_exists(context, product_name):
    """TODO"""
    log.info("Checking if {} already exists".format(product_name))
    res = await api_call(context, "product_show?product=%s" %
                         quote(product_name), data=None)

    try:
        xml = parseString(res)
        # bouncer API returns <products/> if the product doesn't exist
        products_found = len(xml.getElementsByTagName("product"))
        log.info("Products found: {}".format(products_found))
        return bool(products_found)
    except Exception as e:
        log.warning("Error parsing XML: {}".format(e))
        log.warning("Assuming {} does not exist".format(product_name))
        # ignore XML parsing errors
        return False


async def api_add_product(context, product_name, add_locales, ssl_only=False):
    """TODO"""
    data = {
        "product": product_name,
    }
    if add_locales:
        data["languages"] = context.task["payload"]["locales"]
    if ssl_only:
        # Send "true" as a string
        data["ssl_only"] = "true"

    await api_call(context, "product_add/", data)


async def api_add_location(context, product_name, bouncer_platform, path):
    """TODO"""
    data = {
        "product": product_name,
        "os": bouncer_platform,
        "path": path,
    }

    await api_call(context, "location_add/", data)
