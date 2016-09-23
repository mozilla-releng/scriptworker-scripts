import json


def load_json(path):
    with open(path, "r") as fh:
        return json.load(fh)
