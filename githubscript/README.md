# githubscript

Script to handle sensitive operation on Github with Taskcluster. For instance: creating a Github release and publishing Taskcluster artifacts to it.
It's is aimed to be run with [scriptworker](https://github.com/mozilla-releng/scriptworker) (but runs perfectly fine as a standalone script).


## Get the code


First, you need `python>=3.7.0`.

```sh
# create the virtualenv in ./venv3
virtualenv3 venv3
# activate it
. venv3/bin/activate
git clone https://github.com/mozilla-releng/scriptworker-scripts
cd scriptworker-scripts/githubscript
python setup.py develop
```

### Configure

#### config.json
```sh
cp examples/config.example.json config.json
# edit it with your favorite text editor
```

There are many values to edit. Example values should give you a hint about what to provide. If not, please see [signingscript's README](https://github.com/mozilla-releng/scriptworker-scripts/tree/master/signingscript#config-json) for more details about allowing URLs, or contact the author for other unclear areas.

#### directories and file naming

If you aren't running through scriptworker, you need to manually create the directories that `work_dir` points to.  It's better to use new directories for these rather than cluttering and potentially overwriting an existing directory.  Once you set up scriptworker, `work_dir` will be regularly wiped and recreated.


### task.json

```sh
cp examples/task.example.json /path/to/work_dir
# edit it with your favorite text editor
```

Ordinarily, scriptworker would get the task definition from TaskCluster, and write it to a `task.json` in the `work_dir`.  Since you're initially not going to run through scriptworker, you need to put this file on disk yourself.

The important entries to edit are the:
 * `payload.upstreamArtifacts`: tell where the artifacts should be taken from (you need to download and create the directories locally if you run the script outside of scriptworker)
 * `payload.artifactMap`: tell where the artifacts should be uploaded to
 * `dependencies`: need to match the `taskId` in `payload.upstreamArtifacts`.
 * `payload.gitTag`, `payload.gitRevision`, `payload.isPrerelease`, `payload.releaseName`, are the release data given to Github.
 * `scopes`: `project:releng:github:*`, tells which Github project should be updated and what action it will do

### run

You're ready to run githubscript!

```sh
githubscript CONFIG_FILE
```

where `CONFIG_FILE` is the config json you created above.

This should download the file(s) specified in the payload and create or update the Github Release associated to it.

### running through scriptworker

Follow the [scriptworker readme](https://github.com/mozilla-releng/scriptworker/blob/master/README.rst) to set up scriptworker, and use `["path/to/githubscript", "path/to/script_config.json"]` as your `task_script`.

:warning: Make sure your `work_dir` points to the same directories between the scriptworker config and the githubscript config!
