#!/usr/bin/env python

import json
import os

import click
import jsone
import slugid
import yaml


def generate_worker_id(pod_name):
    """
    Generate a worker id based on the pod name it is running in.

    Since the worker id is limited to 38 characters, we slice off `-` delimited
    prefixes, until it fits, since the later components are more relevant for
    identifying a particular worker.
    """
    worker_id = pod_name
    while len(worker_id) > 38 and "-" in worker_id:
        worker_id = worker_id.split("-", 1)[1]
    if not worker_id:
        return slugid.nice().lower().replace("_", "").replace("-", "")
    return worker_id[-38:]


@click.command()
@click.argument("input", type=click.File("r"))
@click.argument("output", type=click.File("w"))
def main(input, output):
    """Convert JSON/YAML templates into using json-e.

       Accepts JSON or YAML format and outputs using JSON because it is YAML
       compatible.
    """
    config_template = yaml.safe_load(input)
    context = os.environ.copy()
    # special case for workerId, it must be unique and max 38 characters long,
    # according to
    # https://docs.taskcluster.net/docs/reference/platform/queue/api#declareWorker
    context["WORKER_ID"] = generate_worker_id(os.environ.get("K8S_POD_NAME", ""))
    config = jsone.render(config_template, context)
    json.dump(config, output, indent=2, sort_keys=True)
