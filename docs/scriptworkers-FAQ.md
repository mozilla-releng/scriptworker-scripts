# FAQ

### How do I deploy changes to a specific scriptworker script?

If you made changes to a specific scriptworker script and you merged your PR, you now have
two options:

* deploy those changes to just that scriptworker script - in which case, push your changes to `production-$script` (e.g.
`production-beetmoverscript` or `production-signingscript`)
* deploy to all of them - in which case, push your changes to `production` and let all the workers be updated

### What happens in a nutshell when we push to the `production` branches?

The Taskcluster CI jobs rebuild the Docker images and push them to the Dockerhub. There are
two pushes happening, one timestamped and one for the `latest` tag, that's to be used
by CloudOps. They have webhooks setup to trigger, at their turn, should there is a new
image pushed. When that happens, their Jenkins pulls that newly pushed image from Docker
and mirrors it in their ecosystem and then deploys it in GCP.

What this means is that, if there are sometimes intermittent issues with the
deployment in the CloudOps world (race condition in downloading docker images or alike)
**rerunning** the latest push-docker-image job from our CI retriggers their deployment
(because timetamped images, rerunning pushes another image even though the underlying
code hasn't changed).

### How do I debug locally an image?

Sometimes the deployments fail for missing environment variables or alike. In order
to debug a production image, one can download that image from Dockerhub and run
it locally. Remember, secrets are passed over via env vars, so you'd have to do something similar
on your local machine:

* for a certain `$script`, hop on `https://hub.docker.com/r/mozilla/releng-{$script}` and
find the latest image pushed
* pull that image locally by `docker pull mozilla/releng-$script:production--$timestamp-$hash`
* use `pass` to define some dummy values replacing the one it'd expect in production (e.g. a file called `local-prod`)
* run the image locally by doing `docker run -ti $(pass show local-prod | grep -v ^# | grep -v '^$' | sed 's/^/-e /')  image_name /bin/bash`

where the format of the file is, e.g.
```
PROJECT_NAME=beetmover
ENV=dev
COT_PRODUCT=mobile
TASKCLUSTER_ROOT_URL=https://firefox-ci-tc.services.mozilla.com
TASKCLUSTER_CLIENT_ID=fake-client
TASKCLUSTER_ACCESS_TOKEN=token
...
```
* once docker container started successfuly, run `./docker.d/init.sh` to simulate what the deployment is doing.


### How to I update a secret in the new world?

Secrets are now stored in SOPS. Once they are updated there, the scriptworkers
need to be (re)taught of their change. In order for that to happen, we need to
redeploy the scriptworkers.

A. Updating an existing secret is easier since it only implies updating SOPS
and rerunning the scriptworkers (one specific or all of them, depending on the branch
chosen when pushing)

B. Adding a new secret needs an extra step, as it needs to be defined in the [cloudops-infra](https://github.com/mozilla-services/cloudops-infra/tree/master/projects/relengworker/k8s/charts)
files. The general rule of thumb to make this is usually:

    1) secrets pushed in SOPS
    2) cloudops-infra PR merged
    3) scriptworker-scripts deployment to pick-up both changes from above

