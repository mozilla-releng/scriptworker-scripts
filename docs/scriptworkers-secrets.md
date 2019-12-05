# Secrets

All secrets are generated from by the CloudOps deployment process, see [example
template](https://github.com/mozilla-services/cloudops-infra/blob/master/projects/relengworker/k8s/charts/beetmover/templates/secret.yaml).

All secrets are passed to the replicas via environment variables and replaced
in the configs using JSON-e or saved to files. In latter case please encode the
contents of the file using `base64 -w0` before handling them to CloudOps, and
use `echo $VAR | base64 -d > file` to save the value into a file in
`init_worker.sh`.

Similarly to environment variables, the secrets use camelCase, and then
converted to SHELL_STYLE. When you pass the secrets to CloudOps, use camelCase
and YAML format. For example:

```yaml
mySecret1: 'supersecretthing'
mySecret1: 'supersecretthing'
```

For secrets transferring, please consult [this mana](https://mana.mozilla.org/wiki/display/SVCOPS/Sharing+a+secret+with+a+coworker) page.
