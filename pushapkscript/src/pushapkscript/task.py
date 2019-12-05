import logging

from scriptworker.exceptions import TaskVerificationError
from scriptworker.utils import get_single_item_from_sequence


log = logging.getLogger(__name__)


def extract_android_product_from_scopes(context):
    prefixes = _get_scope_prefixes(context)
    scopes = context.task['scopes']

    scope, prefix = get_single_item_from_sequence(
        sequence=[(scope, prefix) for scope in scopes for prefix in prefixes],
        condition=lambda scope_then_prefix: scope_then_prefix[0].startswith(scope_then_prefix[1]),
        ErrorClass=TaskVerificationError,
        no_item_error_message='No scope starting with any of these prefixes {} found'.format(prefixes),
        too_many_item_error_message='More than one scope matching these prefixes {} found'.format(prefixes),
    )

    android_product = scope.split(':')[prefix.count(':')]  # the chunk after the prefix is the product name

    return android_product


def _get_scope_prefixes(context):
    prefixes = context.config['taskcluster_scope_prefixes']
    return [
        prefix if prefix.endswith(':') else '{}:'.format(prefix)
        for prefix in prefixes
    ]
