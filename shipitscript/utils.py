import json


def load_json(path):
    with open(path, "r") as fh:
        return json.load(fh)


def get_single_item_from_list(
    list_, condition, ErrorClass=ValueError, no_item_error_message='No item matched condition',
    too_many_item_error_message='Too many items matched condition',
    append_list_to_error_message=True
):
    filtered_list = [item for item in list_ if condition(item)]
    number_of_items_in_filtered_list = len(filtered_list)
    if number_of_items_in_filtered_list == 0:
        error_message = no_item_error_message
    elif number_of_items_in_filtered_list > 1:
        error_message = too_many_item_error_message
    else:
        return filtered_list[0]

    if append_list_to_error_message:
        error_message = '{}. Given: {}'.format(error_message, list_)
    raise ErrorClass(error_message)
