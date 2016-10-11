# Change Log
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## [Unreleased]

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
