import os
import tempfile
import json

from pushsnapscript.utils import load_json


def test_load_json_from_file():
    json_object = {'a_key': 'a_value'}

    with tempfile.TemporaryDirectory() as output_dir:
        output_file = os.path.join(output_dir, 'file.json')
        with open(output_file, 'w') as f:
            json.dump(json_object, f)

        assert load_json(output_file) == json_object
