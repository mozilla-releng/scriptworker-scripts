Change Log
==========
All notable changes to this project will be documented in this file.
This project adheres to `Semantic Versioning <http://semver.org/>`__.

[2.1.0] - 2021-10-25
--------------------
Added
~~~~~
- Upgraded tests to remove python3.7 and add python 3.9

[2.1.0] - 2020-03-30
--------------------
Added
~~~~~
- added merge automation support

[2.0.0] - 2019-11-xx
--------------------
Added
~~~~~
- added l10n bumper support
- added ``treestatus_base_url`` config
- added mypy check
- added black check

Changed
~~~~~~~
- use ``scriptworker_client`` instead of ``scriptworker.client``
- moved src into ``src/treescript`` and tests into ``tests/``

Fixed
~~~~~
- fixed version bumping on relbranches

[1.2.1] - 2019-07-08
--------------------

Changed
~~~~~~~
- Use mozilla-version to ensure new Fennec versions are supported

[1.2.0] - 2019-05-31
--------------------

Added
~~~~~
- Allowed Fennec beta/release version files

[1.1.3] - 2018-10-31
--------------------

Fixed
~~~~~
- Update hg.mozilla.org fingerprint `Bug 1495464 <https://bugzilla.mozilla.org/show_bug.cgi?id=1495464>`__

[1.1.2] - 2018-10-02
--------------------

Fixed
~~~~~
- Update robustcheckout to a version supporting mercurial 4.7.1.

[1.1.1] - 2018-07-27
--------------------

Fixed
~~~~~
- Backed out PR #54 for bustage when the version bump has already happened (PR #69)

[1.1.0] - 2018-07-25
--------------------

Added
~~~~~
- Sanity check that we are pushing the right number of commits. (PR #54)
- Updated robustcheckout from upstream (PR #58)
- Support for pushing with DONTBUILD contributed by @rahul-shiv (PR #59)

[1.0.0] - 2018-06-05
--------------------

Added
~~~~~
- Support for bumping versions with ``esr`` in them.
- Support for thunderbird scope prefixes.
- Support for bumping versions of thunderbird.

[0.4.0]
--------------------

...

[0.1.0] - To Be Released
--------------------
Initial version.
~~~~~~~~~~~~~~~~
