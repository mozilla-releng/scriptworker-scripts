Changelog
=========

All notable changes to this project will be documented in this file.
This project adheres to `Semantic Versioning <http://semver.org/>`__.

.. towncrier release notes start

[8.5.5] = (2019-07-30)
----------------------

Fixed
~~~~~

- Fixed pre-stop.sh process checking logic (`#238
  <https://github.com/mozilla-releng/beetmoverscript/pull/238>`_)



[8.5.4] = (2019-07-29)
----------------------

Added
~~~~~

- Add docker.d/pre-stop.sh script to handle Kubernetes preStop hook. (`#235
  <https://github.com/mozilla-releng/beetmoverscript/pull/235>`_)


[8.5.3] = (2019-07-11)
----------------------

Fixed
~~~~~

- Bugfix in geckoview S3 logic submission. (`#1557269
  <https://bugzilla.mozilla.org/show_bug.cgi?id=1557269>`_)


[8.5.2] = (2019-07-10)
----------------------

Changed
~~~~~~~

- Switched to pip-compile-multi (`PR#230
  <https://github.com/mozilla-releng/beetmoverscript/pull/230>`_)


[8.5.1] = (2019-07-01)
----------------------

Added
~~~~~

- Support for declarative-artifats maven jobs (`#1548545
  <https://bugzilla.mozilla.org/show_bug.cgi?id=1548545>`_)


[8.5.0] = (2019-06-26)
----------------------

Fixed
~~~~~

- Support for stub installers for partner repacks (`#1538995
  <https://bugzilla.mozilla.org/show_bug.cgi?id=1538995>`_)

[8.4.7] = (2019-06-21)
----------------------

Fixed
~~~~~

- Android-Components couldn't ship 1.0.0

[8.4.6] = (2019-05-15)
----------------------

Added
~~~~~

- Add pkg mime type (`#1514903
  <https://bugzilla.mozilla.org/show_bug.cgi?id=1514903>`_)

[8.4.5] = (2019-04-18)
----------------------

Added
~~~~~

- Add support for appservices (`#1536079
  <https://bugzilla.mozilla.org/show_bug.cgi?id=1536079>`_)


Fixed
~~~~~

- Fix buildhub.json in the declarative artifacts world. (`#1539067
  <https://bugzilla.mozilla.org/show_bug.cgi?id=1539067>`_)


[8.4.4] = (2019-04-08)
----------------------

Fixed
~~~~~

- Fix locale and artifact mismatching in the declarative artifacts world. (`#1542500
  <https://bugzilla.mozilla.org/show_bug.cgi?id=1542500>`_)

[8.4.3] = (2019-04-05)
----------------------

Fixed
~~~~~

- Fix buildhub.json in the declarative artifacts world. (`#1539067
  <https://bugzilla.mozilla.org/show_bug.cgi?id=1539067>`_)


[8.4.1] = (2019-02-04)
----------------------

Added
~~~~~

- Add .msi support for Thunderbird (`#1516542
  <https://bugzilla.mozilla.org/show_bug.cgi?id=1516542>`_)


[8.4.0] = (2019-01-25)
----------------------

Added
~~~~~

- Add support for beetmoving win64-aarch64 partner repacks. (`#1522380 <https://bugzilla.mozilla.org/show_bug.cgi?id=1522380>`_)


[8.3.1] = (2018-01-25)
----------------------

Changed
~~~~~~~

- Zip files can now be up to 300MB.

[8.3.0] = (2018-01-02)
----------------------

Changed
~~~~~~~

- Specify `schema_file` internally - users of `beetmoverscript` should no longer set this in config. (`#201 <https://github.com/mozilla-releng/beetmoverscript/pull/201>`_)


[8.2.1] = (2019-12-19)
----------------------

Changed
~~~~~~~

- Resolves issue with buildhub.json download.url. (`#200 <https://github.com/mozilla-releng/beetmoverscript/pull/200>`_)


[8.2.0] = (2018-12-18)
----------------------

Added
~~~~~

- Added support for win64-aarch64 builds. (`#1514407 <https://bugzilla.mozilla.org/show_bug.cgi?id=1514407>`_)


[8.1.1] = (2018-12-18)
----------------------

Fixed
~~~~~

- Bugfix in geckoview in-tree snapshot logic given declarative artifacts.
  (`#1493942 <https://bugzilla.mozilla.org/show_bug.cgi?id=1493942>`_)


[8.1.0] = (2018-12-17)
----------------------

Added
~~~~~

- Support for maven.mozilla.org snapshots releases. (`#1493942
  <https://bugzilla.mozilla.org/show_bug.cgi?id=1493942>`_)


[8.0.0] = (2018-11-28)
-----------------------

Added
~~~~~

- Added suppport for declarative artifacts
  (`#1466714 <https://bugzilla.mozilla.org/show_bug.cgi?id=1466714>`_)

[7.10.2] = (2018-11-07)
-----------------------

Fixed
~~~~~

- Added support for .msi mime types and error out if autodetection of mime types doesn't work. (`#190 <https://bugzilla.mozilla.org/show_bug.cgi?id=190>`_)


[7.10.1] = (2018-11-01)
-----------------------

Added
~~~~~

- Added suppport in Firefox Desktop templates for windows msi installers
  (`#1475512 <https://bugzilla.mozilla.org/show_bug.cgi?id=1475512>`_)


Removed
~~~~~~~

- - drop support for beta/releases of single locale repacks for Fennec
  (`#1408083 <https://bugzilla.mozilla.org/show_bug.cgi?id=1408083>`_)
- Remove `bouncer.apk` from fennec templates as it seems unused. (`#1442684
  <https://bugzilla.mozilla.org/show_bug.cgi?id=1442684>`_)


[7.10.1] = (2018-09-28)
----------------------

Added
~~~~~

- Beetmove updater-dep test package into candidates dir (`#1490119
  <https://bugzilla.mozilla.org/show_bug.cgi?id=1490119>`_)


[7.10.0] = (2018-09-28)
-----------------------

Added
~~~~~

- Handle android-components to be deployed on maven.mozilla.org (`#1491335 <https://bugzilla.mozilla.org/show_bug.cgi?id=1491335>`_)


[7.9.1] = (2018-09-07)
----------------------

Fixed
~~~~~

- Changed geckoview version number format to MAJOR.MINOR.BUILDID. (`#1489132
  <https://bugzilla.mozilla.org/show_bug.cgi?id=1489132>`_)


[7.9.0] = (2018-08-30)
----------------------

Added
~~~~~

- Added support for multiple update formats. (`#1481121
  <https://bugzilla.mozilla.org/show_bug.cgi?id=1481121>`_)


[7.8.2] = (2018-08-29)
----------------------

Fixed
~~~~~
- Changed geckoview folder to maven2/org/mozilla/geckoview/geckoview-* (`#1484932
  <https://bugzilla.mozilla.org/show_bug.cgi?id=1484932>`_)

[7.8.1] = (2018-08-17)
----------------------

Fixed
~~~~~
- Renamed maven bucket to maven-production (`#1470942
  <https://bugzilla.mozilla.org/show_bug.cgi?id=1470942>`_)


[7.8.0] = (2018-08-13)
----------------------

Added
~~~~~
- Support maven on S3. (`#1470942
  <https://bugzilla.mozilla.org/show_bug.cgi?id=1470942>`_)


[7.7.0] = (2018-08-09)
----------------------

Added
~~~~~

- Add support for language pack checksums. (`#1463749
  <https://bugzilla.mozilla.org/show_bug.cgi?id=1463749>`_)


[7.6.0] = (2018-07-20)
----------------------

Added
~~~~~

- support win64-asan-reporter and mac-asan-reporter platforms (`#1473259
  <https://bugzilla.mozilla.org/show_bug.cgi?id=1473259>`_)


[next] = (YYYY-MM-DD)
---------------------

[7.5.0] = (2018-07-02)
----------------------

Added
~~~~~

- Adding support for tests.tar.gz archives for all products (`#733530
  <https://bugzilla.mozilla.org/show_bug.cgi?id=733530>`_)
- adding support for buildhub.json (`#1443873
  <https://bugzilla.mozilla.org/show_bug.cgi?id=1443873>`_)


Fixed
~~~~~

- Fixed coveralls reports (`#1468562
  <https://bugzilla.mozilla.org/show_bug.cgi?id=1468562>`_)


[7.4.0] = (2018-06-12)
----------------------

Changed
~~~~~~~

- Added support to beetmove checksums files for EME-free builds. (`#1422471
  <https://bugzilla.mozilla.org/show_bug.cgi?id=1422471>`_)


[7.3.0] = (2018-06-07)
----------------------

Added
~~~~~

- Added SCOPES.md to exhaustively define all scopes (`#1463456
  <https://bugzilla.mozilla.org/show_bug.cgi?id=1463456>`_)


Removed
~~~~~~~

- - Removed all references and code logic to `balrog_props.json` - Removed all
  `<-->-devedition-devedition` hacks in platforms everywhere - Retired
  `INITIAL_RELEASE_PROPS_FILE` and `IGNORED_UPSTREAM_ARTIFACTS` from
  constants.py - `releaseProperties` is now mandatory for all tasks handled by
  beetmover within the `promote` phase - `balrog_props.json` is no longer
  generated upon completion (`#1449150
  <https://bugzilla.mozilla.org/show_bug.cgi?id=1449150>`_)


Changed
~~~~~~~

- Simplified the relationship behind `stage_platform` and `platform` (`#1449150
  <https://bugzilla.mozilla.org/show_bug.cgi?id=1449150>`_)


Fixed
~~~~~

- Improve requirements.txt docs following python deps everywhere (`#1458329
  <https://bugzilla.mozilla.org/show_bug.cgi?id=1458329>`_)


[7.2.3] = (2018-05-24)
----------------------

Changed
~~~~~~~

- Updated schema to reflect the code. (`#137
  <https://github.com/mozilla-releng/beetmoverscript/issues/137>`_)
- Retire nightly stub installer old format from automation (`Bug 1387021
  <https://bugzilla.mozilla.org/show_bug.cgi?id=1387021>`_) (`#139
  <https://github.com/mozilla-releng/beetmoverscript/issues/139>`_)
- Updated supported python versions to 3.6 and 3.7. (`#140
  <https://github.com/mozilla-releng/beetmoverscript/issues/140>`_, `#141
  <https://github.com/mozilla-releng/beetmoverscript/issues/141>`_)


Fixed
~~~~~

- Fixed capitalization of `Thunderbird` in windows installer and dmg files.
  (`#143 <https://github.com/mozilla-releng/beetmoverscript/issues/143>`_)


[7.2.2] = (2018-05-03)
----------------------

Fixed
~~~~~

- Added `android` to the list platforms to find fennec source packages
  on. (`#137 <https://github.com/mozilla-releng/beetmoverscript/issues/137>`_)



[7.2.1] = (2018-05-03)
----------------------

Fixed
~~~~~

- Added `android-api-16` to the list platforms to find fennec source packages
  on. (`#137 <https://github.com/mozilla-releng/beetmoverscript/issues/137>`_)


[7.2.0] = (2018-05-01)
----------------------

Added
~~~~~

- Added documentation in README for deploying staging `beetmoverscript` packages
- ``CHECKSUMS_CUSTOM_FILE_NAMING`` to hold custom checksums files
- Added template support for source-related checksums file

Removed
~~~~~~~

- Added docs in README for pushing to public pypi


[7.1.1] = (2018-04-26)
----------------------

Fixed
~~~~~

- Fixed fennec support for sources to be on `*-release` platforms. (`#129
  <https://github.com/mozilla-releng/beetmoverscript/issues/129>`_)


[7.1.0] = (2018-04-24)
----------------------

Added
~~~~~

- Added `url_prefix` key to bucket configuration to use for generating balrog
  manifests. (`#122
  <https://github.com/mozilla-releng/beetmoverscript/issues/122>`_)
- Added Thunderbird candidate manifests. (`#123
  <https://github.com/mozilla-releng/beetmoverscript/issues/123>`_)
- Add automatic changelog generation using
  `towncrier <https://github.com/hawkowl/towncrier/>`_. (`#124
  <https://github.com/mozilla-releng/beetmoverscript/issues/124>`_, `#126
  <https://github.com/mozilla-releng/beetmoverscript/issues/126>`_)


Changed
~~~~~~~

- Add multi-locale support to Thunderbird nightly manifests. (`#123
  <https://github.com/mozilla-releng/beetmoverscript/issues/123>`_)
- Update the release instructions to generate wheels. (`#125
  <https://github.com/mozilla-releng/beetmoverscript/issues/125>`_)
- Add support for checksums and sources to be on `*-release` platforms. (`#127
  <https://github.com/mozilla-releng/beetmoverscript/issues/127>`_)


[7.0.0] = (2018-04-18)
----------------------

Added
~~~~~

-  ``PARTNER_REPACK_PRIVATE_REGEXES``, ``PARTNER_REPACK_PUBLIC_REGEXES``
-  ``sanity_check_partner_path`` to make sure the paths are sane
-  Thunderbird nightly templates

Changed
~~~~~~~

-  Partner repacks now pass their paths as ``locale``.
-  Renamed ``get_destination_for_private_repack_path`` to
   ``get_destination_for_partner_repack_path``
-  Partner buckets are now considered "private" if they contain the
   substring ``partner`` in them.

Fixed
~~~~~

-  Fixed ``get_hash`` test on macosx

Removed
~~~~~~~

-  ``PARTNER_LEADING_STRING`` and ``PARTNER_REPACK_PUBLIC_PAYLOAD_ID``

[6.0.1] = (2018-04-12)
----------------------

Fixed
~~~~~

-  Fennec nightly using repack template instead of expected en-US
   template due to 'multi' locale. See PR#120

[6.0.0] = (2018-04-11)
----------------------

Added
~~~~~

-  Thunderbird support (branches, S3 buckets, scopes prefix). You must
   now define ``taskcluster_scope_prefix`` in configuration.
-  Partner repacks support (actions, paths). Configuration may now
   contain partner-related data. See ``config_example.json``.
-  Support for public/private repacks
-  Support for several different locales in
   ``task.payload.upstreamArtifacts``. Bails out if it contradicts
   ``task.payload.locale``

Removed
~~~~~~~

-  ``actions`` in configuration. You don't need to define them anymore
   in configuration
-  ``constants.TEMPLATE_KEY_PLATFORMS`` in favor of
   ``constants.NORMALIZED_FILENAME_PLATFORMS``

[5.1.2] = (2018-04-04)
----------------------

Fixed
~~~~~

-  Add KEY file to candidates directory templates

[5.1.1] = (2018-04-03)
----------------------

Fixed
~~~~~

-  Fix missing "linux-x86\_64-asan-reporter" in Nightly template

[5.1.0] = (2018-03-27)
----------------------

Added
~~~~~

-  support linux64-asan-reporter platform

[5.0.1] = (2018-03-19)
----------------------

Added
~~~~~

-  pretty-named the ``source.tar.xz{,.asc}`` artifacts on s3 to match
   the old tarballs.

[5.0.0] = (2018-03-16)
----------------------

Changed
~~~~~~~

-  ``script.async_main()`` relies on scriptworker (>= 10.2.0) to
   initialize context, config, and task
-  ``task.validate_task_schema()`` now relies on scriptworker

Removed
~~~~~~~

-  ``script.usage()``, now handled by scriptworker

[4.2.0] = (2018-03-15)
----------------------

Added
~~~~~

-  added ``source.tar.xz{,.asc}`` to candidates manifests.

[4.1.0] = (2018-02-28)
----------------------

Added
~~~~~

-  S3 destinations are now logged out.
-  Balrog Props file is not needed anymore if the data is passed in
   ``task.payload.releaseProperties``
-  SUMS and SUMMARY files are now supported
-  Added new linux64-asan platform
-  Defined temporary devedition platforms. They will be removed in
   future versions.

Changed
~~~~~~~

-  Balrog Props file is now a deprecated behavior and will print out a
   warning if used.

[4.0.2] = (2017-12-14)
----------------------

Added
~~~~~

-  beetmoverscript support for Devedition releases
-  ``STAGE_PLATFORM_MAP`` now encompasses the devedition platforms as
   well
-  ``NORMALIZED_BALROG_PLATFORMS`` to correct platforms before writing
   them to balrog manifests
-  support for ``.beet`` files in order to enhance the BBB checksums
-  ``get_product_name`` function to standardize the way to refer to the
   product name based on platform and appName property from balrog props
-  checksums for Fennec
-  SOURCE files for Fennec

Changed
~~~~~~~

-  stop uploading checksums.asc files as ``.beet`` under
   beetmover-checksums
-  ``get_release_props`` and ``update_props`` functions now take context
   as argument

[3.4.0] = (2017-12-05)
----------------------

Added
~~~~~

-  beetmoverscript support to handle in-tree scheduled Firefox releases

Changed
~~~~~~~

-  ``tc_release`` flag in balrog manifest is toggled for any PROMOTION
   or RELEASE types of actions
-  ``partials`` dict in templates is no longer a {``artifact_name``:
   ``build_id``} type of dict, but a {``artifact_name``: ``full_dict``}

[3.3.0] = (2017-11-22)
----------------------

Changed
~~~~~~~

-  jsshell zip files are now to be copied too to from candidates ->
   releases

Fixed
~~~~~

-  push-to-releases behavior now throws an error if no files are to be
   copied

[3.2.0] = (2017-11-6)
---------------------

Added
~~~~~

-  all partial mars are moved under new
   ``pub/firefox/nightly/partials/YYYY/MM/{...}-{branch}`` and
   ``pub/firefox/nightly/partials/YYYY/MM/{...}-{branch}-l10n``
   locations

Fixed
~~~~~

-  locales partial mar are going under their corresponding dated l10n
   folder, instead of the en-US

Removed
~~~~~~~

-  stop publishing partial mars under latest directories for all
   locales, including ``en-US``

[3.1.0] = (2017-10-26)
----------------------

Added
~~~~~

-  ``PRODUCT_TO_PATH`` to map ``fennec`` to ``pub/mobile/``
-  ``get_bucket_name`` to get the aws bucket name from the bucket nick

Fixed
~~~~~

-  ``bucket.objects.filter`` takes kwargs, not an arg.
-  used the aws bucket name instead of the bucket nick for boto3
   operations

[3.0.0] = (2017-10-24)
----------------------

Added
~~~~~

-  added ``PROMOTION_ACTIONS`` and ``is_promotion_action``

Changed
~~~~~~~

-  Renamed ``is_action_a_release_shipping`` to ``is_release_action``
-  removed ``push-to-candidates`` from ``RELEASE_ACTIONS``

Fixed
~~~~~

-  Only use the release task schema for ``RELEASE_ACTIONS``; this was
   breaking fennec beetmover candidates

[2.0.0] = (2017-10-23)
----------------------

Added
~~~~~

-  100% test coverage
-  Added branching in .coveragerc
-  Added py36 testing in travis
-  Added firefox and devedition paths
-  Added ``push-to-releases`` support
-  Added ``RELEASE_EXCLUDE`` list of regexes to avoid copying to
   ``releases/``
-  Added ``release_beetmover_task_schema.json`` for release schema
-  Added ``redo`` dependency
-  Added ``copy_beets``, ``list_bucket_objects``, functions
-  Added ``requirements-{dep,prod}.txt`` for dephash dependency
   tracking.

Changed
~~~~~~~

-  ``TEMPLATE_KEY_PLATFORMS`` is now a standard dict, not a defaultdict
-  scopes checking functions now append messages to raise on, rather
   than raising for each message.

Fixed
~~~~~

-  Removed hardcoded ``tc_nightly`` from balrog manifest; only it adds
   it on nightly actions. On release actions, it adds ``tc_release``.
-  ``setup_logging`` now uses ``logging.INFO`` if not ``verbose``. It
   also reduces ``botocore``, ``boto3``, and ``chardet`` logging to
   ``logging.INFO``.

Removed
~~~~~~~

-  Removed mozilla-aurora from ``RELEASE_BRANCHES``
-  Removed ``push-to-staging`` action

[1.0.0] = (2017-08-28)
----------------------

Added
~~~~~

-  Changelog
-  Support for partials in manifest production for downstream tasks
