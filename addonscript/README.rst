Addonscript
===========

|Build Status| |Coverage Status|

This is designed to be run from scriptworker, but runs perfectly fine as
a standalone script.

Docs
----

``README.md`` is the master readme, and ``README.rst`` is generated via

::

    pandoc --from=markdown --to=rst README.md > README.rst

This is purely because

1. @Callek prefers writing markdown, and
2. pypi appears to deal with rst better than markdown.

.. |Build Status| image:: https://travis-ci.org/mozilla-releng/addonscript.svg?branch=master
   :target: https://travis-ci.org/mozilla-releng/addonscript
.. |Coverage Status| image:: https://coveralls.io/repos/github/mozilla-releng/addonscript/badge.svg?branch=master
   :target: https://coveralls.io/github/mozilla-releng/addonscript?branch=master
