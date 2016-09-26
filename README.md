Signingscript
==============

[![Build Status](https://travis-ci.org/mozilla-releng/pushapkworker.svg?branch=master)](https://travis-ci.org/mozilla-releng/pushapkworker) [![Coverage Status](https://coveralls.io/repos/github/mozilla-releng/pushapkworker/badge.svg?branch=master)](https://coveralls.io/github/mozilla-releng/pushapkworker?branch=master)

Main script that is aimed to be run with [scriptworker](https://github.com/mozilla-releng/scriptworker) (but runs perfectly fine as a standalone script). This project is a fork of [signingscript](https://github.com/mozilla-releng/signingscript). Most of the documentation from signing script applies to this project.

Docs
----
`README.md` is the master readme, and `README.rst` is generated via

    pandoc --from=markdown --to=rst README.md > README.rst

This is purely because

1. @escapewindow prefers writing markdown, and
1. pypi appears to deal with rst better than markdown.


Testing
-------

### virtualenv

First, you need `python>=3.5.0`.

Next, create a python35 virtualenv, and install pushapkworker:

    # create the virtualenv in ./venv3
    virtualenv3 venv3
    # activate it
    . venv3/bin/activate
    # install pushapkworker from pypi
    pip install pushapkworker

If you want to use local clones of [pushapkworker](https://github.com/mozilla-releng/pushapkworker), and/or [scriptworker](https://github.com/mozilla-releng/scriptworker), you can

    python setup.py develop

in each of the applicable directories after, or instead of the `pip install` command.

### config json

The config json looks like this (comments are not valid json, but I'm inserting comments for clarity.  Don't include the comments in the file!):

``` javascript
    {
        // the work directory path.  task.json will live here, as well as downloaded binaries
        "work_dir": "/absolute/path/to/work_dir",
        "schema_file": "pushapkworker/data/signing_task_schema.json",

        // Google Play credentials
        "google_play_service_account": "my-service-account@iam.gserviceaccount.com",
        "google_play_certificate": "/absolute/path/to/googleplay.p12",
        // Package unique name to update
        "google_play_package_name": "org.mozilla.fennec_aurora",

        "jarsigner_binary": "jarsigner",
        "jarsigner_key_store": "/absolute/path/to/keystore",
        "jarsigner_certificate_alias": "certificate-alias-within-keystore",

        // valid URL schemes for the artifacts to download.  A value of `None` will allow any schemes.
        "valid_artifact_schemes": ["https"],
        // valid URL netlocs for the artifacts to download.  A value of `None` will allow any netlocs.
        "valid_artifact_netlocs": ["queue.taskcluster.net"],
        // valid URL path regexes for the artifacts to download.  A value of `None will allow
        // any paths, and the relative filepath of the files will be the entire URL path.
        // If the regexes are defined, the regex MUST define a `filepath`; this will be used
        // as the relative filepath of the file.  If `taskId` is specified in the regex, the
        // taskId MUST match one of the `valid_artifact_task_ids` below.
        "valid_artifact_path_regexes": ["/v1/task/(?P<taskId>[^/]+)(/runs/\\d+)?/artifacts/(?P<filepath>.*)$"],
        // Usually you don't want to specify this in your config file at all.  By default this
        // will default to the `taskId`s of the dependent tasks in the task definition.  If you
        // want to override that, you can override it here.
        "valid_artifact_task_ids": ["VALID_TASK_ID"],
        // enable debug logging
        "verbose": true
    }
```

For more details about allowing URLs, please see [signingscript's README](https://github.com/mozilla-releng/signingscript#config-json).

#### directories and file naming
If you aren't running through scriptworker, you need to manually create the directories that `work_dir` and `artifact_dir` point to.  It's better to use new directories for these rather than cluttering and potentially overwriting an existing directory.  Once you set up scriptworker, the `work_dir` and `artifact_dir` will be regularly wiped and recreated.


### task.json

Ordinarily, scriptworker would get the task definition from TaskCluster, and write it to a `task.json` in the `work_dir`.  Since you're initially not going to run through scriptworker, you need to put this file on disk yourself.

It will look like this:

    {
      "created": "2016-05-04T23:15:17.908Z",
      "deadline": "2016-05-05T00:15:17.908Z",
      "dependencies: [
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
        "unsignedArtifacts": [
          "https://queue.taskcluster.net/v1/task/VALID_TASK_ID/artifacts/FILE_PATH"
        ],
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
        "project:releng:signing:format:gpg"
      ],
      "tags": {},
      "taskGroupId": "CRzxWtujTYa2hOs20evVCA",
      "workerType": "dummy-worker-aki"
    }

The important entries to edit are the `unsignedArtifacts`, the `dependencies`, and the `scopes`.

The `unsignedArtifacts` point to the file(s) to sign; the `dependencies` need to match the `taskId`s of the URLs unless you modify the `valid_artifact_*` config items as specified above.

The first scope, `project:releng:signing:cert:dep-signing`, matches the scope in your password json that you created.  The second scope, `project:releng:signing:format:gpg`, specifies which signing format to use.  (You can specify multiple formats by adding multiple `project:releng:signing:format:` scopes)

Write this to `task.json` in your `work_dir`.

### run

You're ready to run pushapkworker!

    pushapkworker CONFIG_FILE

where `CONFIG_FILE` is the config json you created above.

This should download the file(s) specified in the payload, download a token from the docker-signing-server, upload the file(s) to the docker-signing-server to sign, download the signed bits from the docker-signing-server, and then copy the signed bits into the `artifact_dir`.

### running through scriptworker

Follow the [scriptworker readme](https://github.com/mozilla-releng/scriptworker/blob/master/README.rst) to set up scriptworker, and use `["path/to/pushapkworker", "path/to/script_config.json"]` as your `task_script`.

Make sure your `work_dir` and `artifact_dir` point to the same directories between the scriptworker config and the pushapkworker config!
