Addonscript
==============

[![Build Status](https://travis-ci.org/mozilla-releng/addonscript.svg?branch=master)](https://travis-ci.org/mozilla-releng/addonscript) [![Coverage Status](https://coveralls.io/repos/github/mozilla-releng/addonscript/badge.svg?branch=master)](https://coveralls.io/github/mozilla-releng/addonscript?branch=master)

This is designed to be run from scriptworker, but runs perfectly fine as a standalone script.

Docs
----
More details on what this script does can be found in [RelEng docs](https://moz-releng-docs.readthedocs.io/en/latest/addons/langpacks.html).

`README.md` is the master readme, and `README.rst` is generated via

    pandoc --from=markdown --to=rst README.md > README.rst

This is purely because

1. @Callek prefers writing markdown, and
1. pypi appears to deal with rst better than markdown.


Update python dependencies
--------------------------

The easiest way to do this is to run `pin.sh`:

    ./maintenance/pin.sh addonscript

For python version we use in production:

    $ docker run -ti -v $PWD:/src -w /src python:3.9 /bin/bash
    (docker) /src $ pip install pip-compile-multi
    (docker) /src $ pip-compile-multi -g base -g test

For other python versions:

    $ docker run -ti -v $PWD:/src -w /src python:3.8 /bin/bash
    (docker) /src $ pip install pip-compile-multi
    (docker) /src $ pip-compile-multi -g base -g test -o "py38.txt"

