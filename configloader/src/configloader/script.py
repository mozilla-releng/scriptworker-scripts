#!/usr/bin/env python

import json
import os

import click
import jsone
import slugid
import yaml


@click.command()
@click.option("--worker-id-prefix", default="", help="Worker ID prefix")
@click.argument("input", type=click.File("r"))
@click.argument("output", type=click.File("w"))
def main(worker_id_prefix, input, output):
    """Convert JSON/YAML templates into using json-e.

       Accepts JSON or YAML format and outputs using JSON because it is YAML
       compatible.
    """
    config_template = yaml.safe_load(input)
    context = os.environ.copy()
    # special case for workerId, it must be unique and max 38 characters long,
    # according to
    # https://docs.taskcluster.net/docs/reference/platform/queue/api#declareWorker
    worker_id = worker_id_prefix + slugid.nice().lower().replace("_", "").replace("-", "")
    context["WORKER_ID"] = worker_id[:38]
    config = jsone.render(config_template, context)
    json.dump(config, output, indent=2, sort_keys=True)
