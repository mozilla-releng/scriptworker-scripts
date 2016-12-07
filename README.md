# Balrogscript

A [scriptworker](https://github.com/mozilla-releng/scriptworker) script for pushing artifacts to s3 and submitting metadata to [balrog](https://wiki.mozilla.org/Balrog).

## Configuration
Create a `config.json`, using `config_example.json` as a guide.

At runtime, the following environment variables can be set to override their corresponding `config.json` values:

Scriptworker Specfic:
- `TASKCLUSTER_CLIENT_ID`
- `TASKCLUSTER_ACCESS_TOKEN`
- `SCRIPTWORKER_WORKER_ID`

Balrog Specific:
- `BALROG_API_ROOT`
- `BALROG_USERNAME`
- `BALROG_PASSWORD`
(Optional):
- `S3_BUCKET`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

If any of the S3 credentials are missing, balrogworker will skip uploads
and pass through the taskcluster artifact url directly to balrog. This
can also be manually forced via the `--disable-s3` flag. Note that you
may need to whitelist taskcluster's domain name on your installation of
balrog.

### task.json

The task schema that the program expects is defined in `balrogscript/data/balrog_task_schema.json`

balrogscript will look in `$work_dir/task.json` for the task definition to use.

### manifest.json

The manifest that we use will be in `$work_dir/cot/$upstream_task_id/$path`, based on the `upstreamArtifacts` in the task payload.
