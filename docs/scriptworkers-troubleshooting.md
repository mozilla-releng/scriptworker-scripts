# Troubleshooting

- Check the logs uploaded to Taskcluster.
- Check the Kubernetes container logs. They can be viewed per deployment or per replica.
- Check the [Jenkins logs](https://ops-master.jenkinsv2.prod.mozaws.net/job/gcp-pipelines/job/relengworker/).
- Ask CloudOps ofr help. They can use `kubectl attach` to see what happens in the container.
