# Autoscaling

We use our own way to autoscale the amount of replicas using
[k8s-autoscale](https://github.com/mozilla-releng/k8s-autoscale). It looks at
the pending queue and adjusts the amount of replicas depending on average task
duration, SLA and the maximum amount of replicas we want to run.

The configs can be found in the
[configs](https://github.com/mozilla-releng/k8s-autoscale/tree/master/configs)
directory. Some important config variables are below:

- `worker_type`: corresponds to Taskcluster's `workerType`
- `deployment_namespace`: corresponds to deployment's namespace in Kubernetes
  and used in the Kubernetes API queries.
- `deployment_name`: corresponds to deployment's name in Kubernetes and used in
  the Kubernetes API queries.
- `max_replicas` and `min_replicas`: set the max and min amount of replicas
- `avg_task_duration`: average task duration. Used in calculations and affects
  the amount of replicas we spin up.
- `sla_seconds`: how many seconds we tolerate waiting until we start a pending
  task. For example, with 1 running instance, `sla_seconds` set to 240 and
  `avg_task_duration` set to 60, we don't spin up new instances until we have
  more than 4 pending tasks.
- `capacity_ratio`: a value between 0 and 1, which tells what portion of the
  pending pool this entry can handle. Used in case we want to use multiple
  entries for the same worker type in different clusters.

After a change is merged to the `master` branch, it's immediately deployed to
the dev GCP cluster. In order to deploy the changes to production, you need to
merge from `master` to the `production` branch. Moreover, in order for the change
to have effect in the desired scriptworker(s), a new image for the latter needs
to be pushed out to Docker.
