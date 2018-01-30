import json
# import mock
import os
# import pytest

from treescript.test import tmpdir
import treescript.utils as utils

assert tmpdir  # silence flake8


# load_json {{{1
def test_load_json_from_file(tmpdir):
    json_object = {'a_key': 'a_value'}

    output_file = os.path.join(tmpdir, 'file.json')
    with open(output_file, 'w') as f:
        json.dump(json_object, f)

    assert utils.load_json(output_file) == json_object
