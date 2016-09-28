an implmentation of scriptworker for moving TC artifacts to release buckets


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
> cat /app/beetmoverworker/worker_config.json
{
    "worker_type": "dummy-worker-jlund",
    "worker_id": "dummy-worker-jlund",
    "work_dir": "/app/beetmoverworker/work_dir",
    "log_dir": "/app/beetmoverworker/log_dir",
    "artifact_dir": "/app/beetmoverworker/artifact",
    "task_log_dir": "/app/beetmoverworker/artifact/public/logs",
    "credentials": {
        "accessToken": "...",
        "clientId": "..."
    },
    "task_script": ["/Users/jlund/.virtualenvs/beetmoverscript/bin/beetmoverscript", "/app/beetmoverworker/beetmoverscript/script_config.json"],
    "verbose": true,
    "task_max_timeout": 2400
}
```

```
> cat /app/beetmoverworker/beetmoverscript/script_config.json
{
    "work_dir": "work_dir",
    "artifact_dir": "artifact_dir",
    "verbose": true,
    "template_files": {
        "fennec_nightly": "beetmoverscript/beetmoverscript/templates/fennec_nightly_en_us_multi.yml"
    },
    "s3": {
        "bucket": "mozilla-releng-beetmoverscript",
        "credentials": {
            "id": "...",
            "key": "..."
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
  "taskGroupId": "S-lth0jTThKBjmpt386kUA",
  "dependencies": [
    "YVq4WkdlTmSz4on_FwuGIw"
  ],
  "requires": "all-completed",
  "routes": [],
  "priority": "normal",
  "retries": 5,
  "created": "2016-09-28T02:38:47.963Z",
  "deadline": "2016-09-28T03:38:47.963Z",
  "expires": "2017-08-31T23:20:18.165Z",
  "scopes": [],
  "payload": {
    "maxRunTime": 600,
    "version": "52.0a1",
    "upload_date": 1472747174,
    "artifact_taskid": "YVq4WkdlTmSz4on_FwuGIw",
    "template_key": "fennec_nightly"
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

```
mkvirtualenv --python=/usr/local/bin/python3 beetmoverscript
# currently, beetmoverscript depends on criptworker 0.7.0 + the following patch applied:
#   http://people.mozilla.org/~jlund/scriptworker_add_upload_file_method.patch
# For this reason and also so you can develop on scriptworker itself as you go,
# checkout scriptworker locally and install that custom repo in your venv
git clone https://github.com/mozilla-releng/scriptworker.git
cd scriptworker
# apply http://people.mozilla.org/~jlund/scriptworker_add_upload_file_method.patch
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
