===========================
Scriptworker-scripts Readme
===========================

This is the official mono repo containing all the scriptworker \*scripts.
As to November 2019, we have migrated all the workers, across all trees, to K8s and GCP.
Tagging along, we have also migrated all the individual scripts under the same roof.

Update python dependencies
==========================

::

  # from scriptworker-scripts/ ; this will run docker for py37 and py38
  # for all *scripts
  maintenance/pin.sh
