import logging
import os.path

import scriptworker.client

log = logging.getLogger(__name__)


def get_default_config(base_dir=None):
    base_dir = base_dir or os.path.dirname(os.getcwd())
    default_config = {
        "work_dir": os.path.join(base_dir, "work_dir"),
        "artifact_dir": os.path.join(base_dir, "artifact_dir"),
        "schema_file": os.path.join(os.path.dirname(__file__), "data", "landoscript_task_schema.json"),
    }
    return default_config


async def async_main(context):
    log.info("landoscript running!")
    log.warning("landoscript running!")
    log.debug("landoscript running!")
    log.error("landoscript running!")


def main(config_path=None):
    return scriptworker.client.sync_main(async_main, config_path=config_path, default_config=get_default_config())


__name__ == "__main__" and main()
