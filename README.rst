===========================
Scriptworker-scripts Readme
===========================

This is the official mono repo containing all the scriptworker \*scripts.
As to November 2019, we have migrated all the workers, across all trees, to Kubernetes and Google Compute Cloud.
Tagging along, we have also migrated all the individual scripts under the same roof in order
to single source the shared configurations.

In a nutshell, we now user Docker-based scriptworkers scripts that perform various pieces of our automation.
In order for deploying, we **no longer** rely on `hiera` or `puppet` but on Docker and SOPS.

The comprehensive list of workers that we have available is listed below. They are
split in two large environments within the GCP: `releng-nonprod` and `releng-prod`.

The former holds all the `dev` workers. These are handy to use before submitting
a PR or deployment to production in order to test things out. The environment
holds rules for netflows as well in order to access the dev instances of our
external resources.

The latter, `releng-prod` withhold two sets of workers. The `level-3` workers
which are the production ones. We use these workers to ship the real, production-ready
releases, across our different products (Firefox, Thunderbird, Firefox for mobile related suite, etc).
In the same environment we also have the `level-1` workers which are used for
staging releases. They co-exist here so that they are closer to production
as possible.

Full documentation is available at https://scriptworker-scripts.readthedocs.io/en/latest/index.html.

============================
Overview of existing workers
============================

Note: this is not a comprehensive list. We have added more scripts, more trust domains, and more pools since this list was compiled. The authoritative place to look for currently deployed scriptworkers is in https://github.com/mozilla-services/cloudops-infra/blob/master/projects/relengworker/Jenkinsfile, in the `ScriptWorkerTypes` section. Dev scriptworkers can be found in https://github.com/mozilla-services/cloudops-infra/blob/master/projects/relengworker/Jenkinsfile.dev.

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

pushflatpakscript
-----------------

==================== ============================================
Worker type          Deployment name
==================== ============================================
gecko-1-pushflat-dev pushflat-dev-relengworker-firefoxci-gecko-1
gecko-3-pushflat     pushflat-prod-relengworker-firefoxci-gecko-3
gecko-1-pushflat     pushflat-prod-relengworker-firefoxci-gecko-1
==================== ============================================

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
xpi-3-signing         signing-prod-relengworker-firefoxci-xpi-3-1
xpi-t-signing         signing-prod-relengworker-firefoxci-xpi-t
xpi-t-signing-dev     signing-dev-relengworker-firefoxci-xpi-t-1
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

==========================
Update python dependencies
==========================

::

  # from scriptworker-scripts/ ; this will run docker for py38 and py39
  # for all *scripts to update all the dependencies via `pip-compile-multi`
  $ maintenance/pin.sh

==========================
Testing code changes
==========================

Each directory is a different tool with different testing needs.

When updating the entire set of tools here are a few steps that could help:
 * push changes to `dev` branch (if a single tool, use `dev-<tool>`), wait for deployment in #releng-notifications in Slack
   * `git push --dry-run upstream <my_pr_branch>:dev`
 * do a staging release of an xpi manifest (covers github script, signingscript, shipitscript)
   * add a [change like this](https://github.com/mozilla-releng/staging-xpi-manifest/commit/30c851d859674107431625a23492475ee0707673) to `staging-xpi-manifest`
   * wait for it to be deployed
   * Go to [ShipIt staging](shipit.staging.mozilla-releng.net/) and create a new `XPI Release`, selecting `staging-xpi-public`
   * Once started, go to `xpi releases` and build, promote, ship (need signatures for this) - ensure all jobs complete
   * Make sure to revert changes to any repos
 * do a try push using `-dev` instances running select jobs (covers winsign, beetmoverscript, balrogscript)
   * change [taskcluster/ci/config.yml](https://hg.mozilla.org/try/rev/dd822643ebafd3600032ec3bca5ed60bb941f1cd) to edit the staging machine types:
     * beetmover::staging: '{trust-domain}-1-beetmover' -> '{trust-domain}-1-beetmover-dev'
     * linux-depsigning::worker-type: '{trust-domain}-t-signing' -> '{trust-domain}-t-signing-dev'
     * mac-depsigning::worker-type: 'depsigning-mac-v1' -> 'depsigning-mac-v1-dev' (NOTE: we don't test this)
     * mac-notorization-poller::worker-type: 'mac-notarization-poller' -> 'mac-notarization-poller-dev' (NOTE: we don't test this)
     * mac-signing::staging: 'depsigning-mac-v1' -> 'depsigning-mac-v1-dev' (NOTE: we don't test this)
     * tree::staging: '{trust-domain}-1-tree' -> '{trust-domain}-1-tree-dev'
     * Then run `./mach try fuzzy --full` and select `build-signing`, `release-balrog`, `balrog-en-CA`, `beetmover` jobs.  This will select hundreds of jobs (mostly language repacks), but will get a lot of coverage
 * For all of these (just 1 language pack), examine the logs to ensure using the `-dev` workers and that there are no red flags (like an error that doesn't cause the job to fail)
