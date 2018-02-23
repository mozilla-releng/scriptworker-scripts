import aiohttp
import json
import logging
import sys
import traceback
from xml.dom.minidom import parseString
from urllib.parse import quote
from scriptworker.utils import retry_async


log = logging.getLogger(__name__)


def load_json(path):
    with open(path, "r") as fh:
        return json.load(fh)


async def api_call(context, route, data, error_level='fatal', retry_config=None):
    """TODO"""
    retry_async_kwargs = dict(
        failure_status=None,
        retry_exceptions=(aiohttp.ClientError,
                          aiohttp.ServerTimeoutError),
        error_message="call to %s failed" % (route),
        error_level=error_level,
    )

    if retry_config:
        retry_async_kwargs.update(retry_config)

    await retry_async(_api_call, args=(route, data),
                      **retry_async_kwargs)


async def _api_call(context, route, data):
    """TODO"""
    bouncer_config = context.config["bouncer_config"][context.server]
    credentials = (bouncer_config["username"],
                   bouncer_config["password"])
    api_root = bouncer_config["api_root"]
    api_url = "%s/%s" % (api_root, route)

    kwargs = {'timeout': 60}
    auth = None
    if data:
        kwargs['json'] = data
    if credentials:
        # XXX This may need to be latin1
        auth = aiohttp.BasicAuth(*credentials, encoding='utf-8')
    async with aiohttp.ClientSession(auth=auth) as session:
        log.info("Submitting to %s" % api_url)
        try:
            async with session.post(api_url, **kwargs) as resp:
                log.info("Server response")
                result = await resp.txt()
                log.info(result)
                return result
        except aiohttp.ClientError as e:
            log.warning("Cannot access %s" % api_url)
            traceback.print_exc(file=sys.stdout)
            log.warning("Returned page source:")
            log.warning(e.read())
            raise
        except aiohttp.ServerTimeoutError as e:
            log.warning("Timed out accessing %s: %s" % (api_url, e))
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
