Treescript
==========

|Build Status| |Coverage Status|

This is designed to be run from scriptworker, but runs perfectly fine as
a standalone script.


Update python dependencies
--------------------------

For python version we use in production::

   $ docker run -ti -v $PWD:/src -w /src python:3.7 /bin/bash
   (docker) /src $ pip install pip-compile-multi
   (docker) /src $ pip-compile-multi -g base -g test

For other python versions::

   $ docker run -ti -v $PWD:/src -w /src python:3.6 /bin/bash
   (docker) /src $ pip install pip-compile-multi
   (docker) /src $ pip-compile-multi -g base -g test -o "py36.txt"


.. |Build Status| image:: https://travis-ci.org/mozilla-releng/treescript.svg?branch=master
   :target: https://travis-ci.org/mozilla-releng/treescript
.. |Coverage Status| image:: https://coveralls.io/repos/github/mozilla-releng/treescript/badge.svg?branch=master
   :target: https://coveralls.io/github/mozilla-releng/treescript?branch=master
