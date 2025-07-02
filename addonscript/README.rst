Addonscript
===========

|Build Status|

This is designed to be run from scriptworker, but runs perfectly fine as
a standalone script.

Docs
----

More details on what this script does can be found in `RelEng
docs <https://moz-releng-docs.readthedocs.io/en/latest/addons/langpacks.html>`__.

``README.md`` is the master readme, and ``README.rst`` is generated via

::

   pandoc --from=markdown --to=rst README.md > README.rst

This is purely because

1. @Callek prefers writing markdown, and
2. pypi appears to deal with rst better than markdown.

Update python dependencies
--------------------------

The easiest way to do this is to run ``pin.sh``:

::

   ./maintenance/pin.sh addonscript

.. |Build Status| image:: https://travis-ci.org/mozilla-releng/addonscript.svg?branch=master
   :target: https://travis-ci.org/mozilla-releng/addonscript
