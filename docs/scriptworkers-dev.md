# Dev environment

In case you want to test your changes before pushing to production or
submitting a PR, you can "force push" your changes to the `dev-{script}` (e.g. `dev-beetmoverscript` or `dev-signingscript`)
should you'd like to update only one worker, or the `dev` branch and it
will be deployed to all `dev` workers from the
[nonprod](https://console.cloud.google.com/kubernetes/workload?project=moz-fx-relengwor-nonprod-4a87&organizationId=442341870013&workload_list_tablesize=50)
Kubernetes cluster.

You also need to adjust the in-tree configs to use the `-dev` workerType, e.g.
`gecko-1-beetmover-dev`. If you need to test workers other than gecko, you can
change `init.sh` and/or `init_worker.sh` in order to set proper worker type.
Also you may need to ask CloupdOps to add the corresponding environment
variables or secrets.
