# Changelog
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## [2.0.0] - 2019-05-27
### Added
* Allow specifying the channel in the task payload, rather than scopes.
* Control whether to publish to the snap store via worker config.

### Changed
* Include snapcraft as a dependency, rather than via a submodule.

## [1.0.0] - 2019-03-29
### Changed
* Bumps version to `1.0.0` since `pushsnapscript` is used in production

## [0.2.6] - 2019-03-08
### Fixed
* Package which was missing the embedded snapcraft
* Unpinned requests which is breaking puppet


## [0.2.5] - 2019-03-05
### Changed
* Allow release version numbers on beta (for RCs)


## [0.2.4] - 2018-10-08
### Fixed
* Looking up for an ESR previous snap doesn't raise anymore


## [0.2.3] - 2018-10-03
### Changed
* Task doesn't fail anymore if the snap was either already pushed or already released. It keeps failing if a more recent snap was already released on the given channel.


## [0.2.2] - 2018-09-18
### Changed
* Bumped snapcraft to 2.43.1.


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
