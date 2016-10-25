pushapkscript
=============

|Build Status| |Coverage Status|

Main script that is aimed to be run with
`scriptworker <https://github.com/mozilla-releng/scriptworker>`__ (but
runs perfectly fine as a standalone script). This project is a fork of
`signingscript <https://github.com/mozilla-releng/signingscript>`__.
Most of the documentation from signing script applies to this project.

Get the code
------------

First, you need ``python>=3.5.0``.

::

    # create the virtualenv in ./venv3
    virtualenv3 venv3
    # activate it
    . venv3/bin/activate
    git clone https://github.com/mozilla-releng/pushapkscript
    cd pushapkscript
    pip install pushapkscript

Configure
~~~~~~~~~

::

    cp config_example.json config.json
    # edit it with your favorite text editor

There are many values to edit. Example values should give you a hint
about what to provide. If not, please see `signingscript's
README <https://github.com/mozilla-releng/signingscript#config-json>`__
for more details about allowing URLs, or contact the author for other
unclear areas.

directories and file naming
^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you aren't running through scriptworker, you need to manually create
the directories that ``work_dir`` and ``artifact_dir`` point to. It's
better to use new directories for these rather than cluttering and
potentially overwriting an existing directory. Once you set up
scriptworker, the ``work_dir`` and ``artifact_dir`` will be regularly
wiped and recreated.

task.json
~~~~~~~~~

::

    cp task_example.json /path/to/work_dir
    # edit it with your favorite text editor

Ordinarily, scriptworker would get the task definition from TaskCluster,
and write it to a ``task.json`` in the ``work_dir``. Since you're
initially not going to run through scriptworker, you need to put this
file on disk yourself.

The important entries to edit are the: \* ``apks``: point to the file(s)
to publish to Google Play \* ``dependencies``: need to match the
``taskId``\ s of the URLs unless you modify the ``valid_artifact_*``
config items as specified above \* ``scopes``: the first and only scope,
``project:releng:googleplay:*``, tells which product in Google Play
store should be updated (either
`aurora <https://play.google.com/store/apps/details?id=org.mozilla.fennec_aurora>`__,
`beta <https://play.google.com/store/apps/details?id=org.mozilla.firefox_beta>`__,
or
`release <https://play.google.com/store/apps/details?id=org.mozilla.firefox>`__)
\* ``google_play_track``: refers to which Google Play track (either
production, beta, or alpha) the APK will be uploaded

(aurora, beta, release) vs (alpha, beta, production)?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Google Play allows a product to have 3 different tracks (``alpha``,
``beta``, ``production``). Tracks are used by end-users when they want
to enroll in a beta-testing program.

However, this feature wasn't out when we started publishing Fennec. This
is why Fennec is registred as 3 different product: one for each regular
Firefox channel (aurora, beta, release). As a consequence, here's how
products/tracks should be used.

+----------+--------------------------+---------------+--------+
| Product  | Brand name               | Track         | Notes  |
+==========+==========================+===============+========+
| release  | Firefox                  | ``production` |        |
|          |                          | `             |        |
+----------+--------------------------+---------------+--------+
| beta     | Firefox Beta             | ``production` |        |
|          |                          | `             |        |
+----------+--------------------------+---------------+--------+
| aurora   | Firefox Aurora for       | ``beta``      | produc |
|          | Developers               |               | tion   |
|          |                          |               | is not |
|          |                          |               | used   |
|          |                          |               | to     |
|          |                          |               | show   |
|          |                          |               | the    |
|          |                          |               | produc |
|          |                          |               | t      |
|          |                          |               | is not |
|          |                          |               | aimed  |
|          |                          |               | at     |
|          |                          |               | regula |
|          |                          |               | r      |
|          |                          |               | users  |
+----------+--------------------------+---------------+--------+

Note: For development purpose, aurora on the ``alpha`` track can also be
used.

run
~~~

You're ready to run pushapkscript!

::

    pushapkscript CONFIG_FILE

where ``CONFIG_FILE`` is the config json you created above.

This should download the file(s) specified in the payload, check their
signatures with jarsigner and publish them to Google Play Store.

running through scriptworker
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Follow the `scriptworker
readme <https://github.com/mozilla-releng/scriptworker/blob/master/README.rst>`__
to set up scriptworker, and use
``["path/to/pushapkscript", "path/to/script_config.json"]`` as your
``task_script``.

+---------------------------------------------------------------------------+
| Docs                                                                      |
+===========================================================================+
| ``README.md`` is the master readme, and ``README.rst`` is generated via   |
+---------------------------------------------------------------------------+

Table: warning: Make sure your ``work_dir`` and ``artifact_dir`` point
to the same directories between the scriptworker config and the
pushapkscript config!

::

    pandoc --from=markdown --to=rst README.md > README.rst

This is purely because

1. @escapewindow prefers writing markdown, and
2. pypi appears to deal with rst better than markdown.

.. |Build Status| image:: https://travis-ci.org/mozilla-releng/pushapkscript.svg?branch=master
   :target: https://travis-ci.org/mozilla-releng/pushapkscript
.. |Coverage Status| image:: https://coveralls.io/repos/github/mozilla-releng/pushapkscript/badge.svg?branch=master
   :target: https://coveralls.io/github/mozilla-releng/pushapkscript?branch=master
