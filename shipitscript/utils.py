import json


def load_json(path):
    with open(path, "r") as fh:
        return json.load(fh)


def get_single_item_from_list(
    list_, condition, ErrorClass=ValueError, no_item_error_message='No item matched condition',
    too_many_item_error_message='Too many items matched condition'
):
    filtered_list = [item for item in list_ if condition(item)]
    number_of_items_in_filtered_list = len(filtered_list)
    if number_of_items_in_filtered_list == 0:
        raise ErrorClass('{}. Given: {}'.format(no_item_error_message, list_))
    elif number_of_items_in_filtered_list > 1:
        raise ErrorClass('{}. Given: {}'.format(too_many_item_error_message, list_))

    return filtered_list[0]
