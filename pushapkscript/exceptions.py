from scriptworker.exceptions import ScriptWorkerTaskException
from scriptworker.constants import STATUSES


class SignatureError(ScriptWorkerTaskException):
    def __init__(self, msg):
        super().__init__(msg, exit_code=STATUSES['internal-error'])


class NoGooglePlayStringsFound(Exception):
    def __init__(self, expected_l10n_strings_file_name, upstream_artifacts):
        super().__init__(
            'Could not find "{}" in upstreamArtifacts: {}'.format(expected_l10n_strings_file_name, upstream_artifacts)
        )
