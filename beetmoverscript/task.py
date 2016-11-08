import json
import logging
import os
import scriptworker.client

from beetmoverscript.utils import write_json

log = logging.getLogger(__name__)


def validate_task_schema(context):
    with open(context.config['schema_file']) as fh:
        task_schema = json.load(fh)
    log.debug(task_schema)
    scriptworker.client.validate_json_schema(context.task, task_schema)


def add_balrog_manifest_to_artifacts(context):
    abs_file_path = os.path.join(context.config['artifact_dir'], 'public/manifest.json')
    write_json(abs_file_path, context.balrog_manifest)
