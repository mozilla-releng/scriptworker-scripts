# Changelog
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## [0.2.1] - 2018-04-17
### Added
* Support of the `esr` track. pushsnapscript will release snaps on `esr/stable`. This requires the esr track to be manually created at: https://forum.snapcraft.io/t/firefox-please-create-the-track-esr/5006.

### Changed
* Bumped snapcraft to 2.42.

## [0.2.0] - 2018-04-09
### Changed
* `pushsnapscript.snap_store.push()` doesn't copy macaroon around anymore

### Removed
* `pushsnapscript.utils`

### Fixed
* `pushsnapscript.snap_store.push()` passes a channel list instead of a single channel

## [0.1.0] - 2018-04-04
Initial release
