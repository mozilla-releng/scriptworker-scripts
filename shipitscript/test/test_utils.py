import pytest

from shipitscript.utils import get_single_item_from_sequence


@pytest.mark.parametrize('sequence, condition, expected', (
    (['a', 'b', 'c'], lambda item: item == 'b', 'b'),
    (({'some_key': 1}, {'some_key': 2}, {'some_key': 3}), lambda item: item['some_key'] == 1, {'some_key': 1}),
    (range(1, 10), lambda item: item == 5, 5),
    ({'a': 1, 'b': 2, 'c': 3}.keys(), lambda item: item == 'b', 'b'),
    ({'a': 1, 'b': 2, 'c': 3}.values(), lambda item: item == 2, 2),
))
def test_get_single_item_from_sequence(sequence, condition, expected):
    assert get_single_item_from_sequence(sequence, condition) == expected


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
def test_fail_get_single_item_from_sequence(
    list_, condition, ErrorClass, no_item_error_message, too_many_item_error_message, append_list_to_error_message,
    has_all_params, expected_message
):
    with pytest.raises(ErrorClass) as exec_info:
        if has_all_params:
            get_single_item_from_sequence(
                list_, condition, ErrorClass, no_item_error_message, too_many_item_error_message, append_list_to_error_message
            )
        else:
            get_single_item_from_sequence(list_, condition)

    assert str(exec_info.value) == expected_message
