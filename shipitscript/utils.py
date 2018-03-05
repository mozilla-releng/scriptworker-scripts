

def get_single_item_from_sequence(
    sequence, condition,
    ErrorClass=ValueError,
    no_item_error_message='No item matched condition',
    too_many_item_error_message='Too many items matched condition',
    append_sequence_to_error_message=True
):
    """Returns an item from a python sequence based on the given condition.

    Args:
        sequence (sequence): The sequence to filter
        condition: A function that serves to filter items from `sequence`. Function \
            must have one argument (a single item from the sequence) and return a boolean.
        ErrorClass (Exception): The error type raised in case the item isn't unique
        no_item_error_message (str): The message raised when no item matched the condtion
        too_many_item_error_message (str): The message raised when more than one item matched the condition
        append_sequence_to_error_message (bool): Show or hide what was the tested sequence in the error message.
            Hiding it may prevent sensitive data (such as password) to be exposed to public logs

    Returns:
        The only item in the sequence which matched the condition
    """
    filtered_sequence = [item for item in sequence if condition(item)]
    number_of_items_in_filtered_sequence = len(filtered_sequence)
    if number_of_items_in_filtered_sequence == 0:
        error_message = no_item_error_message
    elif number_of_items_in_filtered_sequence > 1:
        error_message = too_many_item_error_message
    else:
        return filtered_sequence[0]

    if append_sequence_to_error_message:
        error_message = '{}. Given: {}'.format(error_message, sequence)
    raise ErrorClass(error_message)
