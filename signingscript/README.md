Signingscript
==============

[![Build Status](https://travis-ci.org/mozilla-releng/signingscript.svg?branch=master)](https://travis-ci.org/mozilla-releng/signingscript) [![Coverage Status](https://coveralls.io/repos/github/mozilla-releng/signingscript/badge.svg?branch=master)](https://coveralls.io/github/mozilla-releng/signingscript?branch=master)

This is designed to be run from scriptworker, but runs perfectly fine as a standalone script.


Testing
-------

Testing takes a few steps to set up.  Here's how:

### docker-signing-server

To test, you will need to point at a signing server.  Since production signing servers have restricted access and sensitive keys, it's easiest to point at a docker-signing-server instance locally during development.

To do so:

    git clone https://github.com/escapewindow/docker-signing-server
    cd docker-signing-server
    # Follow ./README.md to set up and run the docker instance

Remember the path to `./fake_ca/ca.crt` ; this will be the file that signingscript will use to verify the SSL connection.

### virtualenv

First, you need `python>=3.6.0`.

Next, create a python36 virtualenv, and install signingscript:

    # create the virtualenv in ./venv3
    virtualenv3 venv3
    # activate it
    . venv3/bin/activate
    # install signingscript from pypi
    pip install signingscript

If you want to use local clones of [signingscript](https://github.com/mozilla-releng/signingscript), [signtool](https://github.com/mozilla-releng/signtool), and/or [scriptworker](https://github.com/mozilla-releng/scriptworker), you can

    python setup.py develop

in each of the applicable directories after, or instead of the `pip install` command.

### password json

You'll need a password json file.  The format is

    {
      "BASE_CERT_SCOPE:dep-signing": [
        ["IPADDRESS:PORT", "USERNAME", "PASSWORD", ["SIGNING_FORMAT1", "SIGNING_FORMAT2"...]],
        ["SECOND_IPADDRESS:PORT", "USERNAME", "PASSWORD", ["SIGNING_FORMAT1", "SIGNING_FORMAT2"...]],
        ...
      ],
      "BASE_CERT_SCOPE:nightly-signing": [
        ["IPADDRESS:PORT", "USERNAME", "PASSWORD", ["SIGNING_FORMAT1", "SIGNING_FORMAT2"...]],
        ["SECOND_IPADDRESS:PORT", "USERNAME", "PASSWORD", ["SIGNING_FORMAT1", "SIGNING_FORMAT2"...]],
        ...
      ],
      "BASE_CERT_SCOPE:release-signing": [
        ["IPADDRESS:PORT", "USERNAME", "PASSWORD", ["SIGNING_FORMAT1", "SIGNING_FORMAT2"...]],
        ["SECOND_IPADDRESS:PORT", "USERNAME", "PASSWORD", ["SIGNING_FORMAT1", "SIGNING_FORMAT2"...]],
        ...
      ]
    }

This stripped down version will work with docker-signing-server:

    {
      "project:releng:signing:cert:dep-signing": [
        ["127.0.0.1:9110", "user", "pass", ["gpg"]]
      ]
    }

The user/pass for the docker-signing-server are `user` and `pass` for super sekrit security.

### config json

The config json looks like this (comments are not valid json, but I'm inserting comments for clarity.  Don't include the comments in the file!):


    {
      // path to the password json you created above
      "autograph_configs": "/src/signing/signingscript/example_server_config.json",

      // the work directory path.  task.json will live here, as well as downloaded binaries
      // this should be an absolute path.
      "work_dir": "/src/signing/work_dir",

      // the artifact directory path.  the signed binaries will be copied here for scriptworker to upload
      // this should be an absolute path.
      "artifact_dir": "/src/signing/artifact_dir",

      // the IP that docker-signing-server thinks you're coming from.
      // I got this value from running `docker network inspect bridge` and using the gateway.
      "my_ip": "172.17.0.1",

      // how many seconds should the signing token be valid for?
      "token_duration_seconds": 1200,

      // enable debug logging
      "verbose": true,

      // the path to zipalign. This executable is usually present in $ANDROID_SDK_LOCATION/build-tools/$ANDROID_VERSION/zipalign
      "zipalign": "/absolute/path/to/zipalign",

    }

#### directories and file naming
If you aren't running through scriptworker, you need to manually create the directories that `work_dir` and `artifact_dir` point to.  It's better to use new directories for these rather than cluttering and potentially overwriting an existing directory.  Once you set up scriptworker, the `work_dir` and `artifact_dir` will be regularly wiped and recreated.

Scriptworker will expect to find a config.json for the scriptworker config, so I name the signingscript config json `script_config.json`.  You can name it whatever you'd like.

### file to sign

Put the file(s) to sign somewhere where they can be reached via the web; you'll point to their URL(s) in the task.json below.  Alternately, point to the artifacts of a TaskCluster task, and add the `taskId` to your `dependencies` in the task.json below.

### task.json

Ordinarily, scriptworker would get the task definition from TaskCluster, and write it to a `task.json` in the `work_dir`.  Since you're initially not going to run through scriptworker, you need to put this file on disk yourself.

It will look like this:

    {
      "created": "2016-05-04T23:15:17.908Z",
      "deadline": "2016-05-05T00:15:17.908Z",
      "dependencies": [
        "VALID_TASK_ID"
      ],
      "expires": "2017-05-05T00:15:17.908Z",
      "extra": {},
      "metadata": {
        "description": "Markdown description of **what** this task does",
        "name": "Example Task",
        "owner": "name@example.com",
        "source": "https://tools.taskcluster.net/task-creator/"
      },
      "payload": {
        "upstreamArtifacts": [{
          "taskId": "upstream-task-id1",
          "taskType": "build",
          "paths": ["public/artifact/path1", "public/artifact/path2"],
          "formats": []
        }],
        "maxRunTime": 600
      },
      "priority": "normal",
      "provisionerId": "test-dummy-provisioner",
      "requires": "all-completed",
      "retries": 0,
      "routes": [],
      "schedulerId": "-",
      "scopes": [
        "project:releng:signing:cert:dep-signing",
      ],
      "tags": {},
      "taskGroupId": "CRzxWtujTYa2hOs20evVCA",
      "workerType": "dummy-worker-aki"
    }

The important entries to edit are the `upstreamArtifacts`, the `dependencies`, and the `scopes`.

The `upstreamArtifacts` point to the file(s) to sign.  Because scriptworker downloads and verifies their shas, signingscript expects to find the files under `$work_dir/cot/$upstream_task_id/$path`

The scope, `project:releng:signing:cert:dep-signing`, matches the scope in your password json that you created.

Write this to `task.json` in your `work_dir`.

### run

You're ready to run signingscript!

    signingscript CONFIG_FILE

where `CONFIG_FILE` is the config json you created above.

This should download the file(s) specified in the payload, download a token from the docker-signing-server, upload the file(s) to the docker-signing-server to sign, download the signed bits from the docker-signing-server, and then copy the signed bits into the `artifact_dir`.

### troubleshooting

Invalid json is a common error.  Validate your json with this command:

    python -mjson.tool JSON_FILE

Your docker-signing-server shell should be able to read the `signing.log`, which should help troubleshoot.

### running through scriptworker

[Scriptworker](https://github.com/mozilla-releng/scriptworker) can deal with the TaskCluster specific parts, and run signingscript.

Follow the [scriptworker readme](https://github.com/mozilla-releng/scriptworker/blob/master/README.rst) to set up scriptworker, and use `["path/to/signingscript", "path/to/script_config.json"]` as your `task_script`.

Make sure your `work_dir` and `artifact_dir` point to the same directories between the scriptworker config and the signingscript config!

## Dependency management

This project uses [pip-compile-multi](https://pypi.org/project/pip-compile-multi/) for hard-pinning dependencies versions.
Please see its documentation for usage instructions.
In short, `requirements/base.in` contains the list of direct requirements with occasional version constraints (like `Django<2`)
and `requirements/base.txt` is automatically generated from it by adding recursive tree of dependencies with fixed versions.
The same goes for `test`.

To upgrade dependency versions and hashes, run `pip-compile-multi -g base -g test`.

To add a new dependency without upgrade, add it to `requirements/base.in` and run `pip-compile-multi --no-upgrade -g base -g test`.

For installation always use `.txt` files. For example, command `pip install -Ue . -r requirements/test.txt` will install
this project in test mode, testing requirements and development tools.
Another useful command is `pip-sync requirements/test.txt`, it uninstalls packages from your virtualenv that aren't listed in the file.
