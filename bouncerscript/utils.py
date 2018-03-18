import aiohttp
import logging
from scriptworker.utils import retry_async
from urllib.parse import quote
from xml.dom.minidom import parseString


log = logging.getLogger(__name__)


async def api_call(context, route, data, retry_config=None):
    """Generic api_call method that's to be used as underlying method by
    all the functions working with the bouncer api"""
    retry_async_kwargs = dict(
        retry_exceptions=(aiohttp.ClientError,
                          aiohttp.ServerTimeoutError),
    )

    if retry_config:
        retry_async_kwargs.update(retry_config)

    log.info("Calling {} with data: {}".format(route, data))
    return await retry_async(_do_api_call, args=(context, route, data),
                             **retry_async_kwargs)


async def _do_api_call(context, route, data, method='GET', session=None):
    """Effective function doing the API call to the bouncer API endpoint"""
    session = session or context.session
    bouncer_config = context.config["bouncer_config"][context.server]
    credentials = (bouncer_config["username"],
                   bouncer_config["password"])
    api_root = bouncer_config["api_root"]
    api_url = "%s/%s" % (api_root, route)
    auth = aiohttp.BasicAuth(*credentials)

    kwargs = {'timeout': 60}
    if data:
        kwargs['data'] = data
        method = 'POST'

    try:
        log.info("Performing a {} request to {} with kwargs {}".format(method,
                                                                       api_url,
                                                                       kwargs))
        async with session.request(method, api_url, auth=auth, **kwargs) as resp:
            result = await resp.text()
            log.info("Server response: {}".format(result))
            return result
    except aiohttp.ServerTimeoutError as e:
        log.warning("Timed out accessing %s: %s" % (api_url, e))
        raise
    except aiohttp.ClientError as e:
        log.warning("Cannot access %s: %s" % (api_url, e))
        raise


async def does_product_exists(context, product_name):
    """Function to check if a specific product exists in bouncer already by
    parsing the XML returned by the API endpoint."""
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
    """Function to add a specific product to Bouncer, along with its corresponding
    list of locales"""
    data = {
        "product": product_name,
    }
    if add_locales:
        data["languages"] = context.task["payload"]["locales"]
    if ssl_only:
        # Send "true" as a string
        data["ssl_only"] = "true"

    return await api_call(context, "product_add/", data)


async def api_add_location(context, product_name, bouncer_platform, path):
    """Function to add locations per platform for a specific product"""
    data = {
        "product": product_name,
        "os": bouncer_platform,
        "path": path,
    }

    return await api_call(context, "location_add/", data)


async def api_update_alias(context, alias, product_name):
    """Function to update an aliases to a specific product"""
    data = {
        "alias": alias,
        "related_product": product_name,
    }

    return await api_call(context, "create_update_alias", data)
