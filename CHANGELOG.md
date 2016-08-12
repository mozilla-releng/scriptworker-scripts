# Change Log
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## [Unreleased]
### Changed

- moved repo to github.com/mozilla-releng/signingscript

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
