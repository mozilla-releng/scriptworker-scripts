Change Log
==========

All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

[1.0.1] = (2021-10-25)
----------------------

Changed
~~~~~~~

 - upgraded test environment to remove python 3.7


[1.0.1] - (2019-07-01)
----------------------
Fixed
~~~~~
- wrapped signing and stapling with `retry_async`
- added an `unlock_keychain` call in `sign_all_apps`, in case widevine and omnija signing eat up too much of the unlock window

[1.0.0] - (2019-07-01)
----------------------
Added
~~~~~
- Initial iscript deployment
