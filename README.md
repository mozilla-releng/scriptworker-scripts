an implmentation of scriptworker for moving TC artifacts to release buckets


## install

### locally

#### setup project structure

tl;dr - http://people.mozilla.org/~jlund/beetmover_local_deploy_directory_structure

```
mkdir -p /app/beetmoverworker
cd /app/beetmoverworker
mkdir artifact_dir log_dir work_dir
# create worker_config.json. see https://github.com/mozilla-releng/scriptworker/blob/master/README.rst
touch worker_config.json  # something like http://people.mozilla.org/~jlund/beetmoverscript_configs
# For running outside of scriptworker, i.e. just the beetmover script itself, create a fake task.json.
# If running with scriptworker either task-creator or scheduled in `mach taskgraph`, scriptworker will download this for you
#    automatically once it picks up the respective task from tc queue
touch work_dir/task.json  # something like http://people.mozilla.org/~jlund/beetmoverscript_fake_task.json
git clone https://github.com/lundjordan/beetmoverscript.git
# create beetmoverscript config. see http://people.mozilla.org/~jlund/beetmoverscript_configs
cp beetmoverscript/config_example.json beetmoverscript/script_config.json
```

#### setup py3 venv

```
mkvirtualenv --python=/usr/local/bin/python3 beetmoverscript
# currently, beetmoverscript depends on unreleased version of scriptworker (0.7.0). For this reason and also so
# you can develop on scriptworker itself as you go, checkout scriptworker locally and install that custom repo in your venv
git clone https://github.com/mozilla-releng/scriptworker.git
cd scriptworker
python setup.py develop
# only after first installing your own scriptworker module, install the rest of beetmoverscript's deps
cd /app/beetmoverworker/beetmoverscript
python setup.py develop
```

## usage

***currently only creates manifest and downloads artifacts from tc. upload to s3 is still WIP***

### without scriptworker

```
workon beetmoverscript  # activate venv
cd /app/beetmoverworker
beetmoverscript beetmoverscript/script_config.json  # uses w/e is in work_dir/task.json
```

### with scriptworker (via task-creator in taskcluster tools)

**WARNING: this is broken. beetmoverscript has bitrotted (stale config itesm) from latest scriptworker. Once fixed, see below**

start scriptworker
```
workon beetmoverscript  # activate venv
scriptworker /app/beetmoverworker/worker_config.json
```

create task via that uses same provisioner/worker-type that your scriptworker clientid and config expects:

see https://tools.taskcluster.net/task-creator/ and http://people.mozilla.org/~jlund/beetmoverscript_fake_task.json
