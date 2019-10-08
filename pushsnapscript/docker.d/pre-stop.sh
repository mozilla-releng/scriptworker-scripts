#!/bin/sh

# scriptworker runs as PID 1 in Kubernetes
SCRIPTWORKER_PID=${SCRIPTWORKER_PID:-1}
# See https://kubernetes.io/docs/concepts/workloads/pods/pod/?source=post_page---------------------------#termination-of-pods
# for the details
# Kubernetes executes this script synchronously and waits for it to finish. If
# the script doesn't finish in `terminationGracePeriodSeconds`, it sends
# SIGTERM, waits 2 seconds and kills the container. To prevent this scenario
# in case the task takes too long, this script exits 2 minutes before
# `terminationGracePeriodSeconds` to let scriptworker upload files and report
# `machine-shutdown` to Taskcluster.
POLL_DURATION=1080
POLL_INTERVAL=5

started=$(date +%s)

echo "Sending SIGUSR1 signal to process id $SCRIPTWORKER_PID"

kill -s USR1 $SCRIPTWORKER_PID

while true; do
    echo "checking status..."
    kill -0 $SCRIPTWORKER_PID
    status=$?

    if [ $status -ne 0 ]; then
        echo "Process finished, exiting"
        exit 0
    fi

    now=$(date +%s)
    duration=$[ $now - $started ]

    if [ $duration -gt $POLL_DURATION ]; then
        echo "Waited too long ($duration), giving up"
        exit 1
    fi

    echo "Sleeping for $POLL_INTERVAL"
    sleep $POLL_INTERVAL
done
