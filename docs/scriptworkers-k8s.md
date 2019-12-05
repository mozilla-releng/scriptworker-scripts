# Kuberbnetes

The scriptworkers are hosted in Google Compute Cloud (GCP) using Kubernetes.
The deployment process is managed by the CloudOps team.

If you want to debug the GCP workers in the console, make sure you have access to the GCP console for the
[production](https://console.cloud.google.com/kubernetes/workload?organizationId=442341870013&project=moz-fx-relengworker-prod-a67d&workload_list_tablesize=50)
and
[nonprod](https://console.cloud.google.com/kubernetes/workload?project=moz-fx-relengwor-nonprod-4a87&organizationId=442341870013&workload_list_tablesize=50)
environments. You can get access by filing a bug against CloudOps.

The CloudOps deployment process is managed by Jenkins and the corresponding
files can be found in the
[cloudops-infra](https://github.com/mozilla-services/cloudops-infra/tree/master/projects/relengworker)
repo.

The environment variables are set per deployment and can be found in the
[k8s/values](https://github.com/mozilla-services/cloudops-infra/tree/master/projects/relengworker/k8s/values)
directory. The default values are set in a [separate
file](https://github.com/mozilla-services/cloudops-infra/blob/master/projects/relengworker/k8s/charts/beetmover/values.yaml).
The variables use camelCase, but then converted to SHELL_STYLE in
[configmap.yml](https://github.com/mozilla-services/cloudops-infra/blob/master/projects/relengworker/k8s/charts/beetmover/templates/configmap.yaml)

When Kubernetes decides to stop a worker it gives it 1200s to do this
gracefully, see [the corresponding k8s
config](https://github.com/mozilla-services/cloudops-infra/blob/00c53c02fbe1d8d6e0f77a2d3c20ebd813bd43ab/projects/relengworker/k8s/charts/beetmover/templates/deployment.yaml#L35).
As a part of shutdown process, Kubernetes runs
[docker.d/pre-stop.sh](https://github.com/mozilla-services/cloudops-infra/blob/00c53c02fbe1d8d6e0f77a2d3c20ebd813bd43ab/projects/relengworker/k8s/charts/beetmover/templates/deployment.yaml#L43)
to us enough time to finish running tasks. `docker.d/pre-stop.sh` sends
`SIGUSR1` to scriptworker, what makes it exit as soon as it finishes the
running task. 2 minutes before the deadline `docker.d/pre-stop.sh` exits and
lets Kubernetes send `SIGTERM` what makes scriptworker cancel the task and
upload the logs.

Kubernetes also runs a health check, by calling `docker.d/healthcheck`
periodically. If the script exits non-zero or times out, the corresponding
replica is marked as non healthy and will be removed from the pool.
