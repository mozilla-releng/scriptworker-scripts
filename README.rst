===============================
Signing Worker
===============================

.. image:: https://travis-ci.org/mozilla/signingworker.svg?branch=master
    :target: https://travis-ci.org/mozilla/signingworker

.. image:: https://coveralls.io/repos/mozilla/signingworker/badge.svg
    :target: https://coveralls.io/r/mozilla/signingworker


Signing worker implements `TaskCluster 
<http://docs.taskcluster.net/workers/>`_ worker model for download and 
signing MAR files using `Mozilla Release Engineering signing servers 
<https://wiki.mozilla.org/ReleaseEngineering/Infrastructure/Signing>`_.

Signing workers run on dedicated machines and managed by `puppet 
<http://hg.mozilla.org/build/puppet/file/default/modules/signingworker>`_.

* Free software: MPL2 license
