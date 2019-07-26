# treescript

Tree-related support, e.g. version bumping and tagging.

This is designed to be run from scriptworker, but runs perfectly fine as a standalone script.

# Update python dependencies

For python version we use in production:

   $ docker run -ti -v $PWD:/src -w /src python:3.7 /bin/bash
   (docker) /src $ pip install pip-compile-multi
   (docker) /src $ pip-compile-multi -g base -g test

For other python versions:

   $ docker run -ti -v $PWD:/src -w /src python:3.6 /bin/bash
   (docker) /src $ pip install pip-compile-multi
   (docker) /src $ pip-compile-multi -g base -g test -o "py36.txt"

