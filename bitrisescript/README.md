# bitrisescript

Script to handle triggering [Bitrise]() workflows and pipelines from
Taskcluster. It's is aimed to be run with
[scriptworker](https://github.com/mozilla-releng/scriptworker) (but runs
perfectly fine as a standalone script).


## Get the code


First, you need `python>=3.9`.

```sh
# create the virtualenv in ./venv3
virtualenv3 venv3
# activate it
. venv3/bin/activate
git clone https://github.com/mozilla-releng/scriptworker-scripts
cd scriptworker-scripts/bitrisescript
python setup.py develop
```

### Configure

#### config.json
```sh
cp examples/config.example.json config.json
# edit it with your favorite text editor
```

There are many values to edit. Example values should give you a hint about what
to provide. If not, please see [signingscript's
README](https://github.com/mozilla-releng/scriptworker-scripts/tree/master/signingscript#config-json)
for more details about allowing URLs, or contact the author for other unclear areas.

#### Directories and File Naming

If you aren't running through scriptworker, you need to manually create the
directories that `work_dir` points to.  It's better to use new directories for
these rather than cluttering and potentially overwriting an existing directory.
Once you set up scriptworker, `work_dir` will be regularly wiped and recreated.


### task.json

```sh
cp examples/task.example.json /path/to/work_dir
# edit it with your favorite text editor
```

Ordinarily, scriptworker would get the task definition from TaskCluster, and
write it to a `task.json` in the `work_dir`.  Since you're initially not going
to run through scriptworker, you need to put this file on disk yourself.

The important entries to edit are in the scopes:

 * `project:releng:bitrise:app:*`, tells which Bitrise project should be
   targeted.
 * `project:releng:bitrise:workflow:*`, tells which Bitrise workflows should be
   run.
 * `project:releng:bitrise:pipeline:*`, tells which Bitrise pipelines should be
   run.

### Run

You're ready to run bitrisescript!

```sh
bitrisescript CONFIG_FILE
```

Where `CONFIG_FILE` is the config json you created above.

This should download the file(s) specified in the payload and trigger the
specified Bitrise workflows and pipelines.

### Running through Scriptworker

Follow the [scriptworker
readme](https://github.com/mozilla-releng/scriptworker/blob/master/README.rst)
to set up scriptworker, and use `["path/to/bitrisescript",
"path/to/script_config.json"]` as your `task_script`.

:warning: Make sure your `work_dir` points to the same directories between the
scriptworker config and the bitrisescript config!
