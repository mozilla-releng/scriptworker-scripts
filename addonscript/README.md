Addonscript
==============

[![Build Status](https://travis-ci.org/mozilla-releng/addonscript.svg?branch=master)](https://travis-ci.org/mozilla-releng/addonscript) [![Coverage Status](https://coveralls.io/repos/github/mozilla-releng/addonscript/badge.svg?branch=master)](https://coveralls.io/github/mozilla-releng/addonscript?branch=master)

This is designed to be run from scriptworker, but runs perfectly fine as a standalone script.

Docs
----
More details on what this script does can be found in [RelEng docs](http://docs.mozilla-releng.net/en/latest/addons/addons.html).

`README.md` is the master readme, and `README.rst` is generated via

    pandoc --from=markdown --to=rst README.md > README.rst

This is purely because

1. @Callek prefers writing markdown, and
1. pypi appears to deal with rst better than markdown.


Update python dependencies
--------------------------

For python version we use in production:

    $ docker run -ti -v $PWD:/src -w /src python:3.7 /bin/bash
    (docker) /src $ pip install pip-compile-multi
    (docker) /src $ pip-compile-multi -g base -g test

For other python versions:

    $ docker run -ti -v $PWD:/src -w /src python:3.6 /bin/bash
    (docker) /src $ pip install pip-compile-multi
    (docker) /src $ pip-compile-multi -g base -g test -o "py36.txt"
