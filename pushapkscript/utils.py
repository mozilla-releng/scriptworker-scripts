import json
import logging
import os

log = logging.getLogger(__name__)


def mkdir(path):
    try:
        os.makedirs(path)
        log.info("mkdir {}".format(path))
    except OSError:
        pass


def load_json(path):
    with open(path, "r") as fh:
        return json.load(fh)


def filter_out_identical_values(list_):
    return list(set(list_))
