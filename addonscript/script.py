import aiohttp
import asyncio
import os

import scriptworker.client
from scriptworker.utils import retry_async

from addonscript.api import do_upload, get_upload_status, get_signed_xpi
from addonscript.task import build_filelist
from addonscript.xpi import get_langpack_info


def _craft_aiohttp_connector(context):
    return aiohttp.TCPConnector()


def get_default_config(base_dir=None):
    base_dir = base_dir or os.path.dirname(os.getcwd())
    default_config = {
        'work_dir': os.path.join(base_dir, 'work_dir'),
        'artifact_dir': os.path.join(base_dir, 'artifact_dir'),
        'schema_file': os.path.join(os.path.dirname(__file__), 'data', 'addonscript_task_schema.json'),
    }
    return default_config


async def sign_addon(context, locale):
    upload_data = await retry_async(do_upload, args=(context, locale))
    pk = upload_data['pk']

    upload_status = await retry_async(get_upload_status, args=(context, locale, pk))
    # XXX Encapsulate these sanity check errors in a seperate retried function,
    # because signing may not be instant.
    if len(upload_status['files']) != 1:
        raise Exception("Expected 1 file")
    if (upload_status.get('validation_results') and
            upload_status['validation_results']['errors']):
        raise Exception("Automated Validation produced errors")
    if not upload_status['files'][0]['signed']:
        raise Exception("expected signed xpi")
    destination = os.path.join(context.config['artifact_dir'],
                               'public/build/', locale, 'target.langpack.xpi')
    os.makedirs(os.path.dirname(destination))
    await retry_async(get_signed_xpi,
                      args=(context, upload_status['files'][0]['download_url'],
                            destination))


def build_locales_context(context):
    langpack_info = []
    for f in build_filelist(context):
        current_info = get_langpack_info(context, f)
        langpack_info.append(current_info)
    context.locales = {locale_info['locale']: {
                            'unsigned': locale_info['unsigned'],
                            'version': locale_info['version'],
                            'id': locale_info['id'],
                        }
                       for locale_info in langpack_info}


async def async_main(context):
    connector = _craft_aiohttp_connector(context)
    async with aiohttp.ClientSession(connector=connector) as session:
        context.session = session
        build_locales_context(context)
        tasks = []
        for locale in context.locales:
            tasks.append(asyncio.ensure_future(sign_addon(context, locale)))
        await asyncio.gather(tasks)


def main(config_path=None):
    return scriptworker.client.sync_main(async_main, config_path=config_path,
                                         default_config=get_default_config())


__name__ == '__main__' and main()
