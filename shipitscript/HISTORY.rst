Change Log
==========
All notable changes to this project will be documented in this file.
This project adheres to `Semantic Versioning <http://semver.org/>`__.

4.2.2 - 2021-10-25
--------------------
Changed
~~~~~~~
- Uupgrade test environment to remove python 3.7 and add python 3.9


4.2.2 - 2019-06-07
--------------------
Fixed
~~~~~
- Do not prefix tag version with "v"

4.2.1 - 2019-06-04
--------------------
Changed
~~~~~~~
- Unify docker build and push tasks

4.2.0 - 2019-05-09
--------------------
Added
~~~~~
- Generate docker images as a part of CI

4.1.0 - 2019-05-09
--------------------
Added
~~~~~
- Use special headers to work around https issues

[4.0.0] - 2010-03-06
--------------------
Removed
~~~~~~~
- Removed Ship-it v1 support

[3.2.0] - 2019-03-06
--------------------
Added
~~~~~
- Simplify Ship-it v2 support

[3.1.0] - 2019-01-02
--------------------
Added
~~~~~
- "Nixified" ``shipitscript``

Changed
~~~~~~~
- Specify ``schema_file`` internally - users of ``shipitscript`` should no longer set this in config.

[3.0.0] - 2018-11-19
--------------------
Added
~~~~~
- Added support for marking releases as shipped in Ship-it v2

[2.1.1] - 2018-07-02
--------------------
Fixed
~~~~~
- addressed time comparison properly and not bitwise strings for ``shippedAt`` field separately

[2.1.0] - 2018-07-02
--------------------
Added
~~~~~
- additional validation checks are now being performed to make sure Ship-it side reflects the corresponding values after updating them

[2.0.0] - 2018-06-28
--------------------
Removed
~~~~~~~
- support for py35 in testing

Added
~~~~~
- support for 3.6 and 3.7-dev in testing
- enriched shipitscript to handle multiple behaviors (``mark-as-started`` and ``mark-as-shipped``)
- add coveragerc file
- add badge for Build / Travis in README

[1.0.0] - 2018-03-16
--------------------
Changed
~~~~~~~
- ``script.async_main()`` relies on scriptworker (>= 10.2.0) to:
  - initialize context, config, and task
  - validate the task schema

Removed
~~~~~~~
- ``exceptions.TaskVerificationError`` in favor of the one in scriptworker
- ``script.usage()`` now handled by scriptworker
- ``task.validate_task_schema()`` now handled by scriptworker


[0.1.0] - 2018-01-31
--------------------
Initial release
