# Production environment

After a change is pushed to the `production` branch (or individual per/script
`production-$script`) and passed CI, the CloudOps deployment process gracefully
deploys it to the corresponding [production
deployments](https://console.cloud.google.com/kubernetes/workload?organizationId=442341870013&project=moz-fx-relengworker-prod-a67d&workload_list_tablesize=50).

The deployment status is reported in the `#releng-notifications` Slack channel.
