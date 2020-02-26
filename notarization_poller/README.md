# `notarization_poller`

This is a worker in its own right, and does not run under scriptworker.

Essentially, sometimes Apple's notarization service will take a long time to return with successful notarization. Sometimes it won't even acknowledge that the UUID is in the queue until hours later. Instead of having failing mac signing tasks, we came up with a three-task workflow:

1. Task 1 signs the app, creates and signs the pkg, and submits the app and pkg for notarization. It uploads the signed app and pkg, as well as a manifest with the notarization UUID(s) to poll.

2. Task 2 downloads the manifest with the notarization UUID(s) and polls Apple for status. When Apple returns with a successful notarization (which may take hours), it resolves the task.

3. Task 3 downloads the signed app and pkg, staples the notarization, and uploads the notarized bits.

Tasks (1) and (3) run in `iscript`, using scriptworker.

Task (2) runs under the `notarization_poller`. Because the bulk of the time spent is waiting, we can claim many many tasks in a single worker.
