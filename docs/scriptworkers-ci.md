# Continuous Integration

Every pull request runs unit tests and makes sure that we can build a docker
image. CloudOps deployments happen only when the change is pushed to either
`dev` or `production` branches (or their related `dev-$script` or `prod-$script`
per/script associated branches such as `dev-beetmoverscript` or `prod-signingscript`).
The only exception is the [k8s-autoscale](https://github.com/mozilla-releng/k8s-autoscale) repo, which
deploys to the `nonprod` environment on every push to `master` to make sure we
have the latest version running and tested before we push it to production, and
to the `production` environment, when a change is pushed to the `production`
branch.

In order to debug any issues with the CloudOps deployments make sure you have access to [CloudOps
Jenkins](https://ops-master.jenkinsv2.prod.mozaws.net/job/gcp-pipelines/job/relengworker/).
File a bug similar to [this
one](https://bugzilla.mozilla.org/show_bug.cgi?id=1568649) in order to get
access. You will need to use Duo and SSH proxy in order to access it. See [the
instruction](https://github.com/mozilla-services/cloudops-deployment#accessing-jenkins)
for the details.
