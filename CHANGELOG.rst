Changelog
=========

All notable changes to this project will be documented in this file.
This project adheres to `Semantic Versioning <http://semver.org/>`__.

.. towncrier release notes start

[3.4.0] = (2018-12-18)
----------------------

Added
~~~~~

- Add support for win64-aarch64 builds. (`#1514407 <https://github.com/mozilla-releng/balrogscript/issues/1514407>`_)


[3.3.0] = (2018-11-26)
----------------------

Added
~~~~~

- Imported tests from build-tools. (`#42 <https://github.com/mozilla-releng/balrogscript/issues/42>`_)
- Added `suffixes` to `submit-locale` action to update multiple blobs. (`#43 <https://github.com/mozilla-releng/balrogscript/issues/43>`_)
- Added `update_line` to `submit-toplevel` to create multiple blobs with different update metadata. (`#43 <https://github.com/mozilla-releng/balrogscript/issues/43>`_)


[3.2.1] = (2018-11-21)
----------------------

Removed
~~~~~~~

- Removed dependency on https://hg.mozilla.org/build.tools. (`#40
  <https://github.com/mozilla-releng/balrogscript/issues/40>`_)


[3.2.0] = (2018-08-30)
----------------------

Added
~~~~~

- - Added support for generating blobs for bz2 updates. (`#39
  <https://github.com/mozilla-releng/balrogscript/issues/39>`_)


[3.1.0] = (2018-05-01)
----------------------

Added
~~~~~

- Add support for the thunderbird scope prefixes. (`#32
  <https://github.com/mozilla-releng/balrogscript/issues/32>`_)
- Add automatic changelog generation using
  `towncrier <https://github.com/hawkowl/towncrier/>`_. (`#34
  <https://github.com/mozilla-releng/balrogscript/issues/34>`_)


[3.0.1]
-------

Remove
~~~~~~

-  stubbed out (non working) WNP creation, because the V9 Creator
   doesn't support it

[3.0.0]
-------

Changed
~~~~~~~

-  switched to V9 Creator and Submitter for releases

[2.0.0]
-------

Added
~~~~~

-  added ``balrogscript.constants`` module
-  added support for ``submit-toplevel`` and ``schedule`` actions, for
   releases.

Changed
~~~~~~~

-  the ``schema_file`` string is now a ``schema_files`` dict in config.
-  the ``submit`` action is now ``submit-locale``.
-  ``create_submitter`` is now ``create_locale_submitter``
-  revamped the requirements files.

Removed
~~~~~~~

-  removed channel scope support; these weren't fully fleshed out.

[1.1.0] - 2018-01-09
--------------------

Added
~~~~~

-  ``IOError`` as part of caught exceptions in ``load_config`` for file
   not found issues
-  in testing: release-type manifest, release-type tasks, release-type
   behaviors
-  100% test coverage

Changed
~~~~~~~

-  ``upstream_artifacts`` are no longer baked within the rest of
   ``configs`` because it's counter-intuitive. They lay separately in a
   variable now and play along with the ``task`` definition

Fixed
~~~~~

-  ``task.json`` config is now up-to-date with the release-type changes.
-  ``api_root`` now lies within the server configurations rather than
   outside
-  release manifest sample in testing is now up-to-date

Removed
~~~~~~~

-  ``boto`` logger as it is not used
-  ``KeyError`` exception from ``load_config`` function as no behavior
   could lead there

[1.0.0] = 2017-12-14
--------------------

Added
~~~~~

-  Changelog
-  Support for processing release manifest from beetmover

Fixed
~~~~~

-  fixed some logging
