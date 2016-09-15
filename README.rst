Signingscript
=============

|Build Status| |Coverage Status|

This is designed to be run from scriptworker, but runs perfectly fine as
a standalone script.

Docs
----

``README.md`` is the master readme, and ``README.rst`` is generated via

::

    pandoc --from=markdown --to=rst README.md > README.rst

This is purely because

1. @escapewindow prefers writing markdown, and
2. pypi appears to deal with rst better than markdown.

Testing
-------

Testing takes a few steps to set up. Here's how:

docker-signing-server
~~~~~~~~~~~~~~~~~~~~~

To test, you will need to point at a signing server. Since production
signing servers have restricted access and sensitive keys, it's easiest
to point at a docker-signing-server instance locally during development.

To do so:

::

    git clone https://github.com/escapewindow/docker-signing-server
    cd docker-signing-server
    # Follow ./README.md to set up and run the docker instance

Remember the path to ``./fake_ca/ca.crt`` ; this will be the file that
signingscript will use to verify the SSL connection.

virtualenv
~~~~~~~~~~

First, you need ``python>=3.5.0``.

Next, create a python35 virtualenv, and install signingscript:

::

    # create the virtualenv in ./venv3
    virtualenv3 venv3
    # activate it
    . venv3/bin/activate
    # install signingscript from pypi
    pip install signingscript

If you want to use local clones of
`signingscript <https://github.com/mozilla-releng/signingscript>`__,
`signtool <https://github.com/mozilla-releng/signtool>`__, and/or
`scriptworker <https://github.com/mozilla-releng/scriptworker>`__, you
can

::

    python setup.py develop

in each of the applicable directories after, or instead of the
``pip install`` command.

password json
~~~~~~~~~~~~~

You'll need a password json file. The format is

::

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

::

    {
      "project:releng:signing:cert:dep-signing": [
        ["127.0.0.1:9110", "user", "pass", ["gpg"]]
      ]
    }

The user/pass for the docker-signing-server are ``user`` and ``pass``
for super sekrit security.

config json
~~~~~~~~~~~

The config json looks like this (comments are not valid json, but I'm
inserting comments for clarity. Don't include the comments in the
file!):

::

    {
      // path to the password json you created above
      "signing_server_config": "/src/signing/signingscript/server_config.json",

      // the work directory path.  task.json will live here, as well as downloaded binaries
      // this should be an absolute path.
      "work_dir": "/src/signing/work_dir",

      // the artifact directory path.  the signed binaries will be copied here for scriptworker to upload
      // this should be an absolute path.
      "artifact_dir": "/src/signing/artifact_dir",

      // the IP that docker-signing-server thinks you're coming from.
      // I got this value from running `docker network inspect bridge` and using the gateway.
      "my_ip": "172.17.0.1",

      // the path to the docker-signing-server fake_ca cert that you generated above.
      "ssl_cert": "/src/signing/docker-signing-server/fake_ca/ca.crt",

      // the path to signtool in your virtualenv that you created above
      "signtool": "/src/signing/venv3/bin/signtool",

      // valid URL schemes for the artifacts to download.  A value of `None` will allow any
      // schemes.
      "valid_artifact_schemes": ["https"],

      // valid URL netlocs for the artifacts to download.  A value of `None` will allow any
      // netlocs.
      "valid_artifact_netlocs": ["queue.taskcluster.net"],

      // valid URL path regexes for the artifacts to download.  A value of `None will allow
      // any paths, and the relative filepath of the files will be the entire URL path.
      // If the regexes are defined, the regex MUST define a `filepath`; this will be used
      // as the relative filepath of the file.  If `taskId` is specified in the regex, the
      // taskId MUST match one of the `valid_artifact_task_ids` below.
      "valid_artifact_path_regexes": ["/v1/task/(?P<taskId>[^/]+)(/runs/\d+)?/artifacts/(?P<filepath>.*)$"],

      // Usually you don't want to specify this in your config file at all.  By default this
      // will default to the `taskId`s of the dependent tasks in the task definition.  If you
      // want to override that, you can override it here.
      "valid_artifact_task_ids": ["VALID_TASK_ID"],

      // enable debug logging
      "verbose": true
    }

So, for example, if you want to use a URL like
``http://people.mozilla.org/~asasaki/signing/public/foo/test.mar`` as
your URL, you can allow for it by:

-  adjusting ``valid_artifact_schemes`` to include ``"http"`` (or set it
   to ``None``),
-  adjusting ``valid_artifact_netlocs`` to include
   ``"people.mozilla.org"`` (or set it to ``None``),
-  adjusting ``valid_artifact_path_regexes`` to include
   ``".*/signing/(?P<filepath>.*)$"`` or the like.

Because the above regex doesn't include a ``taskId``, you don't have to
worry about ``valid_artifact_task_ids``. Because ``filepath`` will match
``public/foo/test.mar``, and because we're going to sign with gpg, the
artifacts uploaded will include ``public/foo/test.mar`` and
``public/foo/test.mar.asc``.

directories and file naming
^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you aren't running through scriptworker, you need to manually create
the directories that ``work_dir`` and ``artifact_dir`` point to. It's
better to use new directories for these rather than cluttering and
potentially overwriting an existing directory. Once you set up
scriptworker, the ``work_dir`` and ``artifact_dir`` will be regularly
wiped and recreated.

Scriptworker will expect to find a config.json for the scriptworker
config, so I name the signingscript config json ``script_config.json``.
You can name it whatever you'd like.

file to sign
~~~~~~~~~~~~

Put the file(s) to sign somewhere where they can be reached via the web;
you'll point to their URL(s) in the task.json below. Alternately, point
to the artifacts of a TaskCluster task, and add the ``taskId`` to your
``dependencies`` in the task.json below.

task.json
~~~~~~~~~

Ordinarily, scriptworker would get the task definition from TaskCluster,
and write it to a ``task.json`` in the ``work_dir``. Since you're
initially not going to run through scriptworker, you need to put this
file on disk yourself.

It will look like this:

::

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

The important entries to edit are the ``unsignedArtifacts``, the
``dependencies``, and the ``scopes``.

The ``unsignedArtifacts`` point to the file(s) to sign; the
``dependencies`` need to match the ``taskId``\ s of the URLs unless you
modify the ``valid_artifact_*`` config items as specified above.

The first scope, ``project:releng:signing:cert:dep-signing``, matches
the scope in your password json that you created. The second scope,
``project:releng:signing:format:gpg``, specifies which signing format to
use. (You can specify multiple formats by adding multiple
``project:releng:signing:format:`` scopes)

Write this to ``task.json`` in your ``work_dir``.

run
~~~

You're ready to run signingscript!

::

    signingscript CONFIG_FILE

where ``CONFIG_FILE`` is the config json you created above.

This should download the file(s) specified in the payload, download a
token from the docker-signing-server, upload the file(s) to the
docker-signing-server to sign, download the signed bits from the
docker-signing-server, and then copy the signed bits into the
``artifact_dir``.

troubleshooting
~~~~~~~~~~~~~~~

Invalid json is a common error. Validate your json with this command:

::

    python -mjson.tool JSON_FILE

Your docker-signing-server shell should be able to read the
``signing.log``, which should help troubleshoot.

running through scriptworker
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`Scriptworker <https://github.com/mozilla-releng/scriptworker>`__ can
deal with the TaskCluster specific parts, and run signingscript.

Follow the `scriptworker
readme <https://github.com/mozilla-releng/scriptworker/blob/master/README.rst>`__
to set up scriptworker, and use
``["path/to/signingscript", "path/to/script_config.json"]`` as your
``task_script``.

Make sure your ``work_dir`` and ``artifact_dir`` point to the same
directories between the scriptworker config and the signingscript
config!

.. |Build Status| image:: https://travis-ci.org/mozilla-releng/signingscript.svg?branch=master
   :target: https://travis-ci.org/mozilla-releng/signingscript
.. |Coverage Status| image:: https://coveralls.io/repos/github/mozilla-releng/signingscript/badge.svg?branch=master
   :target: https://coveralls.io/github/mozilla-releng/signingscript?branch=master
