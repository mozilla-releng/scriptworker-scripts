Addonscript
==============

[![Build Status](https://travis-ci.org/mozilla-releng/addonscript.svg?branch=master)](https://travis-ci.org/mozilla-releng/addonscript)

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
