Beetmoverscript README

[![Build Status](https://travis-ci.org/mozilla-releng/beetmoverscript.svg?branch=master)](https://travis-ci.org/mozilla-releng/beetmoverscript)


## deploy a new version to staging

In order to test beetmoverscript changes before reaching production or even before
submitting your PR, please consult the official docs for dev environments within
[scriptworker-scripts](https://scriptworker-scripts.readthedocs.io/en/latest/scriptworkers-dev.html)

## deploy a new version to production

In order to rollout beetmoverscript changes to production please consult the
official docs within [scriptworker-scripts](https://scriptworker-scripts.readthedocs.io/en/latest/scriptworkers-production.html)

## HOWTO - install locally for developing

tl;dr:

```
> tree -L 3 /app/beetmoverworker
/app/beetmoverworker
├── artifact
│   └── public
│       └── logs
├── beetmoverscript -> /Users/jlund/devel/mozilla/dirtyRepos/beetmoverscript  # path to beetmoverscript repo
├── log_dir
│   ├── task_error.log
│   ├── task_output.log
│   └── worker.log
├── work_dir
└── worker_config.json

6 directories, 4 files
```

more detailed:
```
mkdir -p /app/beetmoverworker
cd /app/beetmoverworker
mkdir artifact_dir log_dir work_dir
# create worker_config.json. see https://github.com/mozilla-releng/scriptworker/blob/master/README.rst
touch worker_config.json  # see below for example
git clone https://github.com/lundjordan/beetmoverscript.git
# create beetmoverscript config
cp beetmoverscript/config_example.json beetmoverscript/script_config.json  # see below for example
# For running outside of scriptworker, i.e. just the beetmover script itself, create a fake task.json.
# If running with scriptworker either task-creator or scheduled in `mach taskgraph`, scriptworker will download this for you
#    automatically once it picks up the respective task from tc queue
touch work_dir/task.json  # see below for example
```

```
> cat /app/beetmoverworker/scriptworker.yaml
provisioner_id: test-dummy-provisioner
worker_group: test-dummy-workers
worker_type: dummy-worker-jlund
worker_id: dummy-worker-jlund1
credentials:
   clientId: ...
   accessToken: ...
   certificate: ...

artifact_expiration_hours: 24
artifact_upload_timeout: 1200
task_max_timeout: 2400
verbose: true

task_script: ["/path/to/beetmoverscript_venv/bin/beetmoverscript", "/app/beetmoverworker/beetmoverscript/script_config.json"]

log_dir: "/app/beetmoverworker/log_dir"
work_dir: "/app/beetmoverworker/work_dir"
artifact_dir: "/app/beetmoverworker/artifact"
task_log_dir: "/app/beetmoverworker/artifact/public/logs"

# chainoftrust config
sign_chain_of_trust: true
verify_chain_of_trust: true
verify_cot_signature: true
cot_job_type: beetmover

# gpg homedir config
## only used when verify_chain_of_trust is true
base_gpg_home_dir: "/app/beetmoverworker/gpg"                                                                                 [48/9992]
gpg_lockfile: "/app/beetmoverworker/gpg_homedir.lock"
git_key_repo_dir: "/app/beetmoverworker/key_repo"
git_commit_signing_pubkey_dir: "/app/beetmoverworker/valid_git_fingerprints/"
last_good_git_revision_file: "/app/beetmoverworker/git_revision"
pubkey_path: "/app/beetmoverworker/my_pubkey.asc"
privkey_path: "/app/beetmoverworker/my_privkey.asc"
gpg_path: /usr/local/bin/gpg
my_email: "scriptworker@example.com"
```

```
> cat /app/beetmoverworker/beetmoverscript/script_config.json
{
    "work_dir": "work_dir",
    "artifact_dir": "artifact_dir",
    "verbose": true,
    "aiohttp_max_connections": 5,
    "checksums_digests": ["sha512", "sha256"],
    "actions": {
        "push-to-nightly": {
            "firefox_nightly": "/path/to/beetmoverscript/beetmoverscript/templates/firefox_nightly.yml",
            "firefox_nightly_repacks": "/path/to/beetmoverscript/beetmoverscript/templates/firefox_nightly_repacks.yml",
            "fennec_nightly": "/path/to/beetmoverscript/beetmoverscript/templates/fennec_nightly.yml",
            "fennec_nightly_repacks": "/path/to/beetmoverscript/beetmoverscript/templates/fennec_nightly_repacks.yml",
            "fennecx86_nightly": "/path/to/beetmoverscript/beetmoverscript/templates/fennecx86_nightly.yml"
        },
        "push-to-candidates": {
            "fennec_candidates": "path/to/beetmoverscript/beetmoverscript/templates/fennec_candidates.yml",
            "fennec_candidates_repacks": "path/to/beetmoverscript/beetmoverscript/templates/fennec_candidates_repacks.yml",
            "fennecx86_candidates": "/path/to/beetmoverscript/beetmoverscript/templates/fennecx86_candidates.yml",
            "firefox_candidates": "/path/to/beetmoverscript/beetmoverscript/templates/firefox_candidates.yml",
            "firefox_candidates_repacks": "/path/to/beetmoverscript/beetmoverscript/templates/firefox_candidates_repacks.yml"
            "devedition_candidates": "/path/to/beetmoverscript/beetmoverscript/templates/devedition_candidates.yml",
            "devedition_candidates_repacks": "/path/to/beetmoverscript/beetmoverscript/templates/devedition_candidates_repacks.yml"
        },
        "push-to-releases": {},
        "push-to-staging": {}
    },

    "bucket_config": {
        "nightly": {
            "credentials": {
                "id": "dummy",
                "key": "dummy"
            },
            "buckets": {
                "firefox": "mozilla-releng-firefox-nightly-bucket",
                "fennec": "mozilla-releng-mobile-nightly-bucket"
            }
        },
        "release": {
            "credentials": {
                "id": "dummy",
                "key": "dummy"
            },
            "buckets": {
                "firefox": "mozilla-releng-firefox-release-bucket",
                "fennec": "mozilla-releng-mobile-release-bucket"
            }
        },
        "dep": {
            "credentials": {
                "id": "dummy",
                "key": "dummy"
            },
            "buckets": {
                "firefox": "mozilla-releng-firefox-dep-bucket",
                "fennec": "mozilla-releng-mobile-dep-bucket"
            }
        }
    }
}
```

```
> cat /app/beetmoverworker/work_dir/task.json
{
  "provisionerId": "test-dummy-provisioner",
  "workerType": "dummy-worker-jlund",
  "schedulerId": "-",
  "taskGroupId": "YkE_OQjoTj2G92P4A4Cy1A",
  "dependencies": [
    "c6DPRNsTRa6uVYVp5qCD9w",
    "M4hnMSqcS4itJWC-IwsmXg"
  ],
  "requires": "all-completed",
  "routes": [],
  "priority": "normal",
  "retries": 5,
  "created": "2017-01-08T17:06:07.800Z",
  "deadline": "2017-01-08T18:06:07.800Z",
  "expires": "2017-08-31T23:20:18.165Z",
  "scopes": [
    "project:releng:beetmover:bucket:nightly",
    "project:releng:beetmover:action:push-to-nightly"
  ],
  "payload": {
    "maxRunTime": 600,
    "upload_date": 1483465253,
    "upstreamArtifacts": [
      {
        "paths": [
          "public/build/target.checksums.asc",
          "public/build/target.checksums"
        ],
        "taskId": "M4hnMSqcS4itJWC-IwsmXg",
        "taskType": "build",
        "locale": "en-US"
      }
    ]
  },
  "metadata": {
    "owner": "jlund@mozilla.com",
    "source": "https://tools.taskcluster.net/task-creator/",
    "name": "beetmover fake task",
    "description": ""
  },
  "tags": {},
  "extra": {}
}
```

#### setup py3 venv

##### local

```
mkvirtualenv --python=/usr/local/bin/python3 beetmoverscript
# so you can develop on scriptworker itself as you go,
# checkout scriptworker locally and install that custom repo in your venv
git clone https://github.com/mozilla-releng/scriptworker.git
cd scriptworker
python setup.py develop
# only after first installing your own scriptworker module, install the rest of beetmoverscript's deps
cd /app/beetmoverworker/beetmoverscript
python setup.py develop
```

## usage

### without scriptworker

```
workon beetmoverscript  # activate venv
cd /app/beetmoverworker
beetmoverscript beetmoverscript/script_config.json  # uses w/e is in work_dir/task.json
```

## testing

to run tests (py.test and coverage), use tox (see tox.ini for configuration)
```
$tox
```
