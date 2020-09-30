# Testing scripts locally

Most `*script`s will run locally, or in a local docker container. (Exceptions may include `iscript` and `notarization_poller`, which are targeted to run on mac hardware.)

To test the `*script`s fully locally, you need the secrets. Dep and dev `*script` pools tend to have low-security secrets, so these might be ok to use locally. You may also be able to create your own account(s), e.g. a Google Play account for pushapk testing, or a throwaway gpg key for signing testing.

For a given `*script`, these would be the steps to test on your laptop or docker container:

## Create the `script_config.yaml`

Example `script_config.yaml` files can be found in each `*script`'s `docker.d/worker.yml` file. These are YAML with [json-e](https://github.com/taskcluster/json-e) config so they can support multiple configurations in the same file. You'll want to resolve the json-e portions and just have a simple yaml or json config file.

Your `work_dir` and `artifact_dir` should be absolute paths. You may want to use `$PWD/work` and `$PWD/artifacts`.

## Download a docker image

You can download a docker image built in taskcluster via either `./mach taskgraph load-image` or `taskgraph load-image`, depending on whether you're working from mozilla-central or from a [standalone taskgraph](https://hg.mozilla.org/ci/taskgraph) virtualenv. If you're able to either populate the right secrets via env vars, or start the container interactively, you may be good.

It's also possible to use, say, a python 3 image and create a virtualenv manually.

## Install the virtualenv

Create the virtualenv, e.g. `pyenv virtualenv NAME; pyenv activate NAME`

Next, install the scriptworker-scripts dependencies.
- If your target `*script`'s `setup.py` contains `scriptworker_client`, you want to run `cd scriptworker_client && python setup.py develop && cd ..`
- If your target `*script`'s `setup.py` contains `mozbuild`, you want to run `cd vendored/mozbuild && python setup.py develop && cd ../..`

Then install your `*script`. `cd SCRIPTNAME && python setup.py develop && cd ..`

## Download a task to test

Assuming the `*script` is already live, you can download an existing task and modify it before running. You can do this by:

- Make sure you've installed `scriptworker` in your virtualenv
- `scriptworker` will provide a `create_test_workdir` helper tool.

  ```
  create_test_workdir --help  # for help
  create_test_workdir [--path PATH] [--overwrite] TASK_ID
  ```

  This will create a `./work` directory, populate `./work/task.json` with the task definition of task `TASK_ID`, and download any `task.payload.upstreamArtifacts` in `./work/cot/UPSTREAM_TASK_ID/PATH/TO/ARTIFACT`
- Optionally edit the task.json to test what you want to test. Optionally modify the contents of `./work/cot/...` to test what you want to test.
- Make sure your `script_config.yaml` is pointing at the same path for `work_dir`.
- run `SCRIPTNAME script_config.yaml | tee log` to run the script against that task while capturing log output in a file and the console.
