# pushsnapscript

[![Build Status](https://travis-ci.org/mozilla-releng/pushsnapscript.svg?branch=master)](https://travis-ci.org/mozilla-releng/pushsnapscript) [![Coverage Status](https://coveralls.io/repos/github/mozilla-releng/pushsnapscript/badge.svg?branch=master)](https://coveralls.io/github/mozilla-releng/pushsnapscript?branch=master)

Main script that is aimed to be run with [scriptworker](https://github.com/mozilla-releng/scriptworker) (but runs perfectly fine as a standalone script).


## Get the code


First, you need `python>=3.5.0`.

```sh
virtualenv3 venv3   # create the virtualenv in ./venv3
. venv3/bin/activate # activate it
git clone https://github.com/mozilla-releng/pushsnapscript
cd pushsnapscript
pip install -r requirements/base.txt
python setup.py develop
```

### Configure

#### config.json
```sh
cp examples/config.example.json config.json
# edit it with your favorite text editor
```

There are many values to edit. Example values should give you a hint about what to provide. If not, please see [signingscript's README](https://github.com/mozilla-releng/signingscript#config-json) for more details about allowing URLs, or contact the author for other unclear areas.

#### directories and file naming

If you aren't running through scriptworker, you need to manually create the directories that `work_dir` and `artifact_dir` point to.  It's better to use new directories for these rather than cluttering and potentially overwriting an existing directory.  Once you set up scriptworker, the `work_dir` and `artifact_dir` will be regularly wiped and recreated.


### task.json

```sh
cp examples/task.example.json /path/to/work_dir/task.json
# edit it with your favorite text editor
```

Ordinarily, scriptworker would get the task definition from TaskCluster, and write it to a `task.json` in the `work_dir`.  Since you're initially not going to run through scriptworker, you need to put this file on disk yourself.

The important entries to edit are the:
 * `upstreamArtifacts`: point to the file(s) to publish to Google Play
 * `dependencies`: need to match the `taskId`s of the URLs unless you modify the `valid_artifact_*` config items as specified above
 * `scopes`: the first and only scope, `project:releng:snapcraft:*`, tells which channel on Snap store should be updated. For more details about scopes. See `scopes.md`


### run

You're ready to run pushsnapscript!

```sh
pushsnapscript CONFIG_FILE
```


where `CONFIG_FILE` is the config json you created above.

### running through scriptworker

Follow the [scriptworker readme](https://github.com/mozilla-releng/scriptworker/blob/master/README.rst) to set up scriptworker, and use `["path/to/pushsnapscript", "path/to/script_config.json"]` as your `task_script`.

:warning: Make sure your `work_dir` and `artifact_dir` point to the same directories between the scriptworker config and the pushsnapscript config!
