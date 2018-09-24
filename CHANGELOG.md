# Change Log
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## [9.0.1] - 2018-09-17
### Fixed
- Initialize a hardcoded datadog statsd port of 8135 to avoid conflicting with collectd.

## [9.0.0] - 2018-09-17
### Changed
- Configuration: `taskcluster_scope_prefix` now becomes `taskcluster_scope_prefixes` and takes a JSON array.

## [8.0.1] - 2018-08-23
### Fixed
- fix typo in setup.py that caused the wrong package to be required

## [8.0.0] - 2018-08-22
### Added
- support for signing MARs and APKs with Autograph

## [7.0.4] - 2018-08-06
### Fixed
- catch `aiohttp.ClientError` and `asyncio.TimeoutError` during `get_token` requests

## [7.0.3] - 2018-07-27
### Changed
- remove the taskcluster pinning
- require py37 tests to be green

### Fixed
- create tarballs with root-owned files

## [7.0.2] - 2018-07-23
### Fixed
- Removed the old ssl cert, as this caused bustage.

## [7.0.1] - 2018-07-23
### Changed
- Updated the set of valid ssl certs

## [7.0.0] - 2018-05-10
### Added
- Added aiohttp3 support

### Changed
- Dropped py35 support; added py37 tests
- Packaged README.md

### Removed
- Removed README.rst

## [6.1.0] - 2018-04-24
### Added
- Added focus-jar support

## [6.0.1] - 2018-04-04
### Added
- Create `KEY` artifact when doing GPG signing

## [6.0.0] - 2018-03-14
### Changed
- `script.async_main()` relies on scriptworker (>= 10.2.0) to:
  - initialize context, config, and task
  - validate the task schema

### Removed
- `exceptions.TaskVerificationError` in favor of the one in scriptworker
- `script.SigningContext`, `script.usage()`, `script.main()` now handled by scriptworker
- `task.validate_task_schema()` now handled by scriptworker


## [5.0.0] - 2018-02-01
### Added
- support for different scope prefix (was hardcoded to `project:releng:signing:`). Prefixes are now defined in the configuration under `taskcluster_scope_prefix`.
- certificates of MDC1 datacenter.

### Changed
- `task_cert_type()` now lives under the `task` module.

## [4.2.1] - 2017-12-05
### Added
- added additional dependency for datadog statsd

## [4.2.0] - 2017-11-30
### Added
- added datadog statsd

## [4.1.2] - 2017-08-30
### Added
- updated `host.cert` for new ssl cert with >30day expiration :)

## [4.1.1] - 2017-08-30
### Added
- updated `host.cert` for new ssl cert

## [4.1.0] - 2017-08-15
### Added
- added `signingscirpt.createprecomplete` from [mozilla-central](https://hg.mozilla.org/mozilla-central/file/d3025e55dfc3/config/createprecomplete.py), and made it py3 compatible
- added a `remove_extra_files` to make sure we're not leaving any cruft behind in the extracted directories.

### Changed
- widevine zip signing now extracts the entire zipfile
- regenerate the `precomplete` file after widevine signing, for complete updates. then upload a `precomplete.diff`.

## [4.0.4] - 2017-08-15
### Fixed
- pass in the .sig path in `sign_widevine_zip` as well.

## [4.0.3] - 2017-08-15
### Fixed
- pass in the .sig path now that `output_file` works in signtool

## [4.0.2] - 2017-08-15
### Fixed
- widevine signing for mac now places sigfiles in `Contents/Resources/` instead of `Contents/MacOS/`. Given a path with an `.app` inside a `.app`, on the rightmost `Contents/MacOS/` path is changed.

## [4.0.1] - 2017-08-15
### Changed
- widevine signing now happens before macapp.

## [4.0.0] - 2017-08-14
### Added
- `sign_widevine_zip` only extracts the files we need to sign, and appends the sigfiles to the original zipfile.
- `sign_widevine_tar` extracts the entire tarball, and recreates it with the sigfiles added. This is because compressed tarballs can't be appended to.
- `get_zipfile_files` and `get_tarfile_files` lets us list the contents of an archive without extracting.
- `_get_widevine_signing_files` takes a list of file paths, and returns a dictionary of `{path: signing_format, ...}`. If a file to sign exists, but its `.sig` file also exists, we no longer mark that file for re-signing.

### Changed
- `sign_signcode` now extracts to a new temp dir every time, to optimize for task runtime speed (no more nuking the same temp dir to reuse). This temp dir is under `work_dir`, so it should be cleaned up after the task is finished.
- `sign_widevine` now calls `sign_widevine_zip` or `sign_widevine_tar` as needed.
- `_extract_zipfile` now allows for specifying a `files` kwarg. If specified, only extract those paths. If not, extract everything.
- `_create_zipfile` now allows for appending, via the new `mode` kwarg.

## [3.0.2] - 2017-08-09
### Fixed
- fixed `widevine_blessed` signing.

## [3.0.1] - 2017-08-07
### Fixed
- supported signtool signing for non-zip files (e.g., setup.exe)

## [3.0.0] - 2017-08-04
### Added
- widevine support
- new `signingscript.sign` module

### Changed
- refactored the whole signing workflow for more testability and less fragility

## [2.0.1] - 2017-07-27
### Fixed
- compressed zipfiles

## [2.0.0] - 2017-05-31
### Added
- windows zipfile signing support.
- `SigningScriptError`
- py36 test support

### Changed
- Moved the `aiohttp.ClientSession` creation into `async_main`
- No longer close the event loop at the end of `main`
- `sign_file` no longer takes a `to` kwarg; we always overwrite the original file, due to zipfile signing logic.

### Fixed
- `pytest-asyncio` 0.6.0 compatibility

## [1.0.0] - 2017-03-23
### Added
- `example_server_config.json`
- 100% test coverage, with full docstrings and `flake8_docstrings`
- moved `SigningServer` named tuple out of function, for easier importing and reuse

### Changed
- no longer accept `dmgv2` format
- explode and tar dmg files (support dmg signing in taskcluster)
- `get_default_config` now takes a `base_dir` kwarg
- moved `_execute_subprocess` to utils
- `sign_file` now returns the path to the target file
- `async_main` now copies the returned path to the `artifact_dir`

### Fixed
- close the event loop on `main()` exception

## [0.10.1] - 2017-02-09
### Fixed
- Fix an execution error due to the addition of zipalign

## [0.10.0] - 2017-02-08
### Changed
- zipalign APKs in order to allow them to be published onto Google Play Store

## [0.9.0] - 2016-12-08
### Changed
- look at `work_dir` for the downloaded artifacts, to match the latest scriptworker changes

## [0.8.2] - 2016-11-28
### Added
- added `token_duration_seconds` config item

### Changed

### Fixed
- updated readme to describe `upstreamArtifacts` rather than `unsignedArtifacts`.

### Removed
- `valid_artifact_*` config items, as well as references to them in the readme.

## [0.8.1] - 2016-11-28
### Fixed
- bumped the token timeout to 20min

## [0.8.0] - 2016-11-09
## Changed
- `copy_to_artifact_dir` is now `copy_to_dir`, and takes a `parent_dir` arg.

## Fixed
- copy `upstreamArtifacts` files from `artifact_dir` to `work_dir` before signing.  This means we no longer overwrite chain of trust artifacts with signed artifacts

## [0.7.1] - 2016-11-09
## Fixed
- only copy files that aren't already in the appropriate `artifact_dir` location

## [0.7.0] - 2016-11-09
### Changed
- changed the task definition to use `upstreamArtifacts`, which allows for different sets of signing formats per file
- stopped downloading artifacts; now we use the pre-downloaded files from scriptworker's chain of trust verification

## [0.6.0] - 2016-10-10
### Changed
- moved `download_artifacts` and `download_files` to scriptworker; compatible with `scriptworker>=0.7.0`

### Fixed
- noted that the various `*_dir`s need to be absolute paths.

### Removed
- `DownloadError`, which is now in scriptworker, and `ChecksumMismatchError`, which wasn't used.

## [0.5.1] - 2016-08-29
### Added
- `README.md` is now checked in.  Generate `README.rst` via pandoc.

### Changed
- update the READMEs to describe how the new `validate_artifact_url` calls change testing.
- `scriptworker.client.validate_task_schema` -> `scriptworker.client.validate_json_schema`

### Fixed
- `valid_artifact_regexes` should be spelled `valid_artifact_path_regexes`.  fixed.

## [0.5.0] - 2016-08-19
### Changed
- `unsignedArtifacts` URLs will now be verified as valid TaskCluster artifact URLs for dependent tasks by default.
- tests no longer use nosetest syntax; they've been all ported to pytest syntax.

### Fixed
- multiple `unsignedArtifacts` with different paths but the same filenames will no longer clobber each other.

## [0.4.2] - 2016-08-17
### Changed
- moved signingscript.worker functions into signingscript.task

### Fixed
- `download_files` now uses the standard SSL trusted CAs.

## [0.4.1] - 2016-08-16
### Fixed
- bustage fix - import error, list.keys() error.  someday we'll have 100% coverage

## [0.4.0] - 2016-08-15
### Added

- documented how to test signingscript in `README.rst`.

### Changed

- switched from `task.payload.signingManifest` to `task.payload.unsignedArtifacts`.

### Removed

- cleaned up the old CONTRIBUTING.rst and nix files.

## [0.3.0] - 2016-08-12
### Changed

- moved repo to github.com/mozilla-releng/signingscript

### Fixed

- fixed non-gpg signing - don't always expect an .asc file

## [0.2.1] - 2016-08-11
### Changed

- no longer accept old host.cert

## [0.2.0] - 2016-08-10
### Changed

- reverted from calver before productionizing
- updated host.cert to include `releng_CA`
- reduced token duration
- cleaned up logging

### Fixed

- fixed `aiohttp>=0.22.0` (auth no longer takes a tuple)
- fixed mac docker signing
