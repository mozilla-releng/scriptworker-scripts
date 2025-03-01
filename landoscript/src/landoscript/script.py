import logging
import os.path

import scriptworker.client

from landoscript.actions import version_bump
from landoscript.types import Config, Context

log = logging.getLogger(__name__)


def get_default_config(base_dir: str = "") -> Config:
    base_dir = base_dir or os.path.dirname(os.getcwd())
    default_config = {
        "work_dir": os.path.join(base_dir, "work_dir"),
        "artifact_dir": os.path.join(base_dir, "artifact_dir"),
        "schema_file": os.path.join(os.path.dirname(__file__), "data", "landoscript_task_schema.json"),
    }
    return default_config


async def async_main(context: Context):
    config = context["config"]
    payload = context["task"]["payload"]
    for action in payload["actions"]:
        if action == "version_bump":
            version_bump.run(config, payload["repo"], payload["branch"], payload["version_bump_info"])


def main(config_path=None):
    return scriptworker.client.sync_main(async_main, config_path=config_path, default_config=get_default_config())


if __name__ == "__main__":
    main()
