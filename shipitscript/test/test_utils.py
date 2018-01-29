import os
import pytest
import tempfile
import json

from shipitscript.utils import load_json, get_single_item_from_list


def test_load_json_from_file():
    json_object = {'a_key': 'a_value'}

    with tempfile.TemporaryDirectory() as output_dir:
        output_file = os.path.join(output_dir, 'file.json')
        with open(output_file, 'w') as f:
            json.dump(json_object, f)

        assert load_json(output_file) == json_object


@pytest.mark.parametrize('list_, condition, expected', (
    (['a', 'b', 'c'], lambda item: item == 'b', 'b'),
    ([{'some_key': 1}, {'some_key': 2}, {'some_key': 3}], lambda item: item['some_key'] == 1, {'some_key': 1}),
))
def test_get_single_item_from_list(list_, condition, expected):
    assert get_single_item_from_list(list_, condition) == expected


class SomeCustomError(Exception):
    pass


@pytest.mark.parametrize(
 'list_, condition, ErrorClass, no_item_error_message, too_many_item_error_message, append_list_to_error_message, \
 has_all_params, expected_message', (
    (['a', 'b', 'c'], lambda item: item == 'z', SomeCustomError, 'NO ITEM', 'TOO MANY', True, True, "NO ITEM. Given: ['a', 'b', 'c']"),
    (['a', 'b', 'c'], lambda item: item == 'z', SomeCustomError, 'NO ITEM', 'TOO MANY', False, True, 'NO ITEM'),
    (['a', 'b', 'b'], lambda item: item == 'b', SomeCustomError, 'NO ITEM', 'TOO MANY', True, True, "TOO MANY. Given: ['a', 'b', 'b']"),
    (['a', 'b', 'c'], lambda _: False, ValueError, None, None, None, False, "No item matched condition. Given: ['a', 'b', 'c']"),
    (['a', 'b', 'c'], lambda _: True, ValueError, None, None, None, False, "Too many items matched condition. Given: ['a', 'b', 'c']"),
 )
)
def test_fail_get_single_item_from_list(
    list_, condition, ErrorClass, no_item_error_message, too_many_item_error_message, append_list_to_error_message,
    has_all_params, expected_message
):
    with pytest.raises(ErrorClass) as exec_info:
        if has_all_params:
            get_single_item_from_list(
                list_, condition, ErrorClass, no_item_error_message, too_many_item_error_message, append_list_to_error_message
            )
        else:
            get_single_item_from_list(list_, condition)

    assert str(exec_info.value) == expected_message
