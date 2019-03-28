#!/usr/bin/env python
"""scriptworker-client constants.

Attributes:
    STATUSES (dict): maps taskcluster status (string) to exit code (int).

"""

# These should mirror `scriptworker.constants.STATUSES`.
STATUSES = {
    "success": 0,
    "failure": 1,
    "worker-shutdown": 2,
    "malformed-payload": 3,
    "resource-unavailable": 4,
    "internal-error": 5,
    "superseded": 6,
    "intermittent-task": 7,
}
