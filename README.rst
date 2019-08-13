Shipitscript
============

|Build Status| |Coverage Status|


Deployment
----------

Shipit scriptworker is deployed to GCP using Mozilla Cloudops infrastructure
and deployment process. The scriptworkers are deployed in the same Kubernetes
cluster with Ship-It API in order to access it.


Deployment to "dev" environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

After a change is pushed to the `master` branch, CI generates a docker image
and pushes it to the `mozilla/shipitscript`_ repository using the `latest` tag.
After a few minutes the Cloudpops pipeline automatically deploys the image to
the `scriptworker-dev-shipitapi-app-1` workload in the `shipitapi-nonprod` GCP
project. The worker type is set to `shipit-dev` and it should handle maple and
try based releases. The configuration templates can be found under the
`docker.d/configs/dev` directory of this repository.

Deployment to "production" environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In order to deploy a change to production it has to be tagged, released,
deployed to stage, and promoted to production. Some steps are manual and some
require the CloudOps Team.

Tag a particular revision using the following command:::

   git tag -s $(cat version.txt)

Push the tag:::

   git push origin $(cat version.txt)

CI will run tests, build a docker image, but the image will not be pushed to
the docker repository.

Create a github release using the tag pushed in the previous step. This action
will trigger a CI task group which will run tests, build and push the docker
image to the repository using the git tag as the docker tag. For example, the
`3.4.5` git tag will generate `mozilla/shipitscript:3.4.5` docker image.

After a few minutes the Cloudops pipeline should copy the docker image to GCR.
For example, the `mozilla/shipitscript:3.4.5` is copied as
`gcr.io/moz-fx-cloudops-images-global/gcp-pipelines/shipitapi/scriptworker/shipitapi:3.4.5`.

The scriptworkers are automatically deployed to the
`scriptworker-stage-shipitapi-app-1` workload in the `shipitapi-nonprod` GCP
project. The worker type is set to
`shipit-dev` and it should handle maple and try based releases. The
configuration templates can be found under the `docker.d/configs/staging`
directory of this repository.

### Ask Cloudops to promote to production
After the stage environment is validated, it can be promoted to production by
explicitly asking someone from the Cloudops team to do so.

The scriptworkers are deployed to the `scriptworker-prod-shipitapi-app-1`
workload in the `shipitapi-prod` GCP project. The worker type is set to
`shipit-v1` and it should handle production releases. The configuration
templates can be found under the `docker.d/configs/production` directory of
this repository.

.. |Build Status| image:: https://travis-ci.org/mozilla-releng/shipitscript.svg?branch=master
   :target: https://travis-ci.org/mozilla-releng/shipitscript
.. |Coverage Status| image:: https://coveralls.io/repos/github/mozilla-releng/shipitscript/badge.svg?branch=master
   :target: https://coveralls.io/github/mozilla-releng/shipitscript?branch=master
.. _`mozilla/shipitscript`: https://hub.docker.com/r/mozilla/shipitscript

