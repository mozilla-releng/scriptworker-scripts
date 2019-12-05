===========================
Scriptworker-scripts Readme
===========================

This is the official mono repo containing all the scriptworker \*scripts.
As to November 2019, we have migrated all the workers, across all trees, to K8s and GCP.
Tagging along, we have also migrated all the individual scripts under the same roof.

============================
Overview of existing workers
============================

addonscript
-----------

================= =========================================
Worker type       Deployment name
================= =========================================
gecko-1-addon-dev addon-dev-relengworker-firefoxci-gecko-1
gecko-3-addon     addon-prod-relengworker-firefoxci-gecko-3
gecko-1-addon     addon-prod-relengworker-firefoxci-gecko-1
================= =========================================

balrogscript
------------

================== ===========================================
Worker type        Deployment name
================== ===========================================
gecko-1-balrog-dev balrog-dev-relengworker-firefoxci-gecko-1
gecko-3-balrog     balrog-prod-relengworker-firefoxci-gecko-3
gecko-1-balrog     balrog-prod-relengworker-firefoxci-gecko-1
comm-3-balrog      balrog-prod-relengworker-firefoxci-comm-3
comm-1-balrog      balrog-prod-relengworker-firefoxci-comm-1
================== ===========================================

beetmoverscript
---------------

+-------------------------+-------------------------------------------------------------+
| Worker type             | Deployment name                                             |
+=========================+=============================================================+
| gecko-1-beetmover-dev   | beetmover-dev-relengworker-firefoxci-gecko-1                |
+-------------------------+-------------------------------------------------------------+
| gecko-3-beetmover       | beetmover-prod-relengworker-firefoxci-gecko-3               |
+-------------------------+-------------------------------------------------------------+
| gecko-1-beetmover       | beetmover-prod-relengworker-firefoxci-gecko-1               |
+-------------------------+-------------------------------------------------------------+
| comm-3-beetmover        | beetmover-prod-relengworker-firefoxci-comm-3                |
+-------------------------+-------------------------------------------------------------+
| appservices-3-beetmover | beetmover-prod-relengworker-firefoxci-applicationservices-3 |
+-------------------------+-------------------------------------------------------------+
| appservices-1-beetmover | beetmover-prod-relengworker-firefoxci-applicationservices-1 |
+-------------------------+-------------------------------------------------------------+
| mobile-3-beetmover      | beetmover-prod-relengworker-firefoxci-mobile-3              |
+-------------------------+-------------------------------------------------------------+
| mobile-1-beetmover      | beetmover-prod-relengworker-firefoxci-mobile-1              |
+-------------------------+-------------------------------------------------------------+

bouncerscript
-------------

=================== ===========================================
Worker type         Deployment name
=================== ===========================================
gecko-1-bouncer-dev bouncer-dev-relengworker-firefoxci-gecko-1
gecko-3-bouncer     bouncer-prod-relengworker-firefoxci-gecko-3
gecko-1-bouncer     bouncer-prod-relengworker-firefoxci-gecko-1
comm-3-bouncer      bouncer-prod-relengworker-firefoxci-comm-3
=================== ===========================================

pushapkscript
-------------

=================== ============================================
Worker type         Deployment name
=================== ============================================
gecko-1-pushapk-dev pushapk-dev-relengworker-firefoxci-gecko-1
gecko-3-pushapk     pushapk-prod-relengworker-firefoxci-gecko-3
gecko-1-pushapk     pushapk-prod-relengworker-firefoxci-gecko-1
mobile-3-pushapk    pushapk-prod-relengworker-firefoxci-mobile-3
mobile-1-pushapk    pushapk-prod-relengworker-firefoxci-mobile-1
=================== ============================================

pushsnapscript
--------------

==================== ============================================
Worker type          Deployment name
==================== ============================================
gecko-1-pushsnap-dev pushsnap-dev-relengworker-firefoxci-gecko-1
gecko-3-pushsnap     pushsnap-prod-relengworker-firefoxci-gecko-3
gecko-1-pushsnap     pushsnap-prod-relengworker-firefoxci-gecko-1
==================== ============================================

shipitscript
------------

================== ==========================================
Worker type        Deployment name
================== ==========================================
gecko-1-shipit-dev shipit-dev-relengworker-firefoxci-gecko-1
gecko-3-shipit     shipit-prod-relengworker-firefoxci-gecko-3
gecko-1-shipit     shipit-prod-relengworker-firefoxci-gecko-1
comm-3-shipit      shipit-prod-relengworker-firefoxci-comm-3
comm-1-shipit      shipit-prod-relengworker-firefoxci-comm-1
================== ==========================================

signingscript
-------------

===================== =========================================================
Worker type           Deployment name
===================== =========================================================
gecko-1-shipit-dev    shipit-dev-relengworker-firefoxci-gecko-1
gecko-3-signing       signing-prod-relengworker-firefoxci-gecko-3
gecko-t-signing       signing-prod-relengworker-firefoxci-gecko-t
mobile-3-signing      signing-prod-relengworker-firefoxci-mobile-3
mobile-t-signing      signing-prod-relengworker-firefoxci-mobile-t
comm-3-signing        signing-prod-relengworker-firefoxci-comm-3
comm-t-signing        signing-prod-relengworker-firefoxci-comm-t
appservices-3-signing signing-prod-relengworker-firefoxci-applicationservices-3
appservices-t-signing signing-prod-relengworker-firefoxci-applicationservices-t
===================== =========================================================

treescript
----------

================ ========================================
Worker type      Deployment name
================ ========================================
gecko-1-tree-dev tree-dev-relengworker-firefoxci-gecko-1
gecko-3-tree     tree-prod-relengworker-firefoxci-gecko-3
gecko-1-tree     tree-prod-relengworker-firefoxci-gecko-1
comm-3-tree      tree-prod-relengworker-firefoxci-comm-3
================ ========================================

Update python dependencies
==========================

::

  # from scriptworker-scripts/ ; this will run docker for py37 and py38
  # for all *scripts
  maintenance/pin.sh
