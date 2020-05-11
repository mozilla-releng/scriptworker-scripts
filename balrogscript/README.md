# Balrogscript

[![Build Status](https://travis-ci.org/mozilla-releng/balrogscript.svg?branch=master)](https://travis-ci.org/mozilla-releng/balrogscript)
[![Coverage Status](https://coveralls.io/repos/github/mozilla-releng/balrogscript/badge.svg?branch=master)](https://coveralls.io/github/mozilla-releng/balrogscript?branch=master)

A [scriptworker](https://github.com/mozilla-releng/scriptworker) script for submitting metadata to [balrog](https://wiki.mozilla.org/Balrog).

## Configuration
Create a `config.json`, using `config_example.json` as a guide.

At runtime, the following environment variables can be set to override their corresponding `config.json` values:

Scriptworker Specific:
- `TASKCLUSTER_CLIENT_ID`
- `TASKCLUSTER_ACCESS_TOKEN`
- `SCRIPTWORKER_WORKER_ID`

Balrog Specific:
- `BALROG_API_ROOT`

### task.json

The task schema that the program expects is defined in `balrogscript/data/balrog_ACTION_schema.json`

balrogscript will look in `$work_dir/task.json` for the task definition to use.

### manifest.json

The manifest that we use will be in `$work_dir/cot/$upstream_task_id/$path`, based on the `upstreamArtifacts` in the task payload.

## dephash note

It looks like dephash is [busted on python 2.7](https://github.com/escapewindow/dephash/issues/5).

To update `requirements-prod.txt`,

```bash
pip install pip-tools
pip-compile --generate-hashes requirements-dev.txt -o requirements-prod.txt
```
