import logging

from scriptworker.exceptions import TaskVerificationError
from scriptworker.utils import get_single_item_from_sequence


log = logging.getLogger(__name__)


def extract_android_product_from_scopes(context):
    prefix = context.config['taskcluster_scope_prefix']
    scope = get_single_item_from_sequence(
        context.task['scopes'],
        condition=lambda scope: scope.startswith(prefix),
        ErrorClass=TaskVerificationError,
        no_item_error_message='No valid scope found. Task must have a scope that starts with "{}"'.format(prefix),
        too_many_item_error_message='More than one valid scope given',
    )

    android_product = scope[len(prefix):]

    return android_product
