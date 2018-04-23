Beetmoverscript README

[![Build Status](https://travis-ci.org/mozilla-releng/beetmoverscript.svg?branch=master)](https://travis-ci.org/mozilla-releng/beetmoverscript)
[![Coverage Status](https://coveralls.io/repos/github/mozilla-releng/beetmoverscript/badge.svg?branch=master)](https://coveralls.io/github/mozilla-releng/beetmoverscript?branch=master)


## deploy a new version

1. Once your PR is reviewed and passes the tests, have one of the admins review & merge it
1. Bump to new version in `beetmoverscript/_version.py`.
1. `towncrier`
1. Commit with a "%VERSION%" message
1. `git tag -s %VERSION%`
1. `git push`
1. `git push --tags`
1. Create wheel with `python3 setup.py bdist_wheel` and scp that file under [puppet](http://releng-puppet2.srv.releng.scl3.mozilla.com/python/packages-3.5/)
1. Wait for that file to be synchronized across all puppet instances (emails arrive to confirm that)
1. Tweak the `beetmoverscript` version under [beetmoverworker module](https://hg.mozilla.org/build/puppet/file/default/modules/beetmover_scriptworker/manifests/init.pp#l28) to reflect the new value
1. Push puppet bump to `default` branch, wait for tests to run and confirmation to arrive in `#releng`. Merge it to `production` after that.
1. There are currently fifteen prod and ten dev beetmoverworkers. Ssh to each and single one of them (csshX?) and run `puppet agent --test` as `root` to enforce the deployment of the newest catalog. Can also wait for the cron job to run puppet to deploy new changes every 30 mins or so.
1. Create a tarball with `python3 setup.py sdist` and upload the tarball and wheel to pypi with

```
twine upload dist/beetmoverscript-${VERSION}.tar.gz dist/beetmoverscript-${VERSION}-py3-none-any.whl
```


## install

### locally

#### setup project structure

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
    "schema_file": "/app/beetmoverworker/beetmoverscript/beetmoverscript/data/beetmover_task_schema.json",
    "aiohttp_max_connections": 10,
    "checksums_digests": ["sha512", "sha256"],
    "blobs_needing_prettynaming_contents": [
        "target.test_packages.json"
    ],
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
          "public/build/balrog_props.json"
        ],
        "taskId": "c6DPRNsTRa6uVYVp5qCD9w",
        "taskType": "build",
        "locale": "en-US"
      },
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

### with scriptworker (via task-creator in taskcluster tools)

start scriptworker
```
workon beetmoverscript  # activate venv
scriptworker /app/beetmoverworker/worker_config.json
```

create task via that uses same provisioner/worker-type that your scriptworker clientid and config expects:

see https://tools.taskcluster.net/task-creator/ and example here: https://queue.taskcluster.net/v1/task/S-lth0jTThKBjmpt386kUA

## testing

to run tests (py.test and coverage), use tox (see tox.ini for configuration)
```
$tox
```
