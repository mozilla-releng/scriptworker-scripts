from scriptworker.exceptions import TaskVerificationError


class AlreadyLatestError(TaskVerificationError):
    def __init__(self, latest_released_version, latest_released_revision):
        super(AlreadyLatestError, self).__init__(
            'Version "{}" (revision {}) is already the latest one. No need to release it.'.format(
                latest_released_version, latest_released_revision
            )
        )
