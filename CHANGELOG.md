# Changelog
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## [4.1.0] - 2018-02-28

### Added
- S3 destinations are now logged out.
- Balrog Props file is not needed anymore if the data is passed in `task.payload.releaseProperties`
- SUMS and SUMMARY files are now supported
- Added new linux64-asan platform
- Defined temporary devedition platforms. They will be removed in future versions.

### Changed
- Balrog Props file is now a deprecated behavior and will print out a warning if used.

## [4.0.2] - 2017-12-14

### Added
- beetmoverscript support for Devedition releases
- `STAGE_PLATFORM_MAP` now encompasses the devedition platforms as well
- `NORMALIZED_BALROG_PLATFORMS` to correct platforms before writing them to balrog manifests
- support for `.beet` files in order to enhance the BBB checksums
- `get_product_name` function to standardize the way to refer to the product name based on platform and appName property from balrog props
- checksums for Fennec
- SOURCE files for Fennec

### Changed
- stop uploading checksums.asc files as `.beet`  under beetmover-checksums
- `get_release_props` and `update_props`  functions now take context as argument

## [3.4.0] - 2017-12-05
### Added
- beetmoverscript support to handle in-tree scheduled Firefox releases

### Changed
- `tc_release` flag in balrog manifest is toggled for any PROMOTION or RELEASE types of actions
- `partials` dict in templates is no longer a {`artifact_name`: `build_id`} type of dict, but a {`artifact_name`: `full_dict`}

## [3.3.0] - 2017-11-22
### Changed
- jsshell zip files are now to be copied too to from candidates -> releases

### Fixed
- push-to-releases behavior now throws an error if no files are to be copied

## [3.2.0] - 2017-11-6
### Added
- all partial mars are moved under new `pub/firefox/nightly/partials/YYYY/MM/{...}-{branch}` and `pub/firefox/nightly/partials/YYYY/MM/{...}-{branch}-l10n` locations

### Fixed
- locales partial mar are going under their corresponding dated l10n folder, instead of the en-US

### Removed
- stop publishing partial mars under latest directories for all locales, including `en-US`

## [3.1.0] - 2017-10-26
### Added
- `PRODUCT_TO_PATH` to map `fennec` to `pub/mobile/`
- `get_bucket_name` to get the aws bucket name from the bucket nick

### Fixed
- `bucket.objects.filter` takes kwargs, not an arg.
- used the aws bucket name instead of the bucket nick for boto3 operations

## [3.0.0] - 2017-10-24
### Added
- added `PROMOTION_ACTIONS` and `is_promotion_action`

### Changed
- Renamed `is_action_a_release_shipping` to `is_release_action`
- removed `push-to-candidates` from `RELEASE_ACTIONS`

### Fixed
- Only use the release task schema for `RELEASE_ACTIONS`; this was breaking fennec beetmover candidates

## [2.0.0] - 2017-10-23
### Added
- 100% test coverage
- Added branching in .coveragerc
- Added py36 testing in travis
- Added firefox and devedition paths
- Added `push-to-releases` support
- Added `RELEASE_EXCLUDE` list of regexes to avoid copying to `releases/`
- Added `release_beetmover_task_schema.json` for release schema
- Added `redo` dependency
- Added `copy_beets`, `list_bucket_objects`, functions
- Added `requirements-{dep,prod}.txt` for dephash dependency tracking.

### Changed
- `TEMPLATE_KEY_PLATFORMS` is now a standard dict, not a defaultdict
- scopes checking functions now append messages to raise on, rather than raising for each message.

### Fixed
- Removed hardcoded `tc_nightly` from balrog manifest; only it adds it on nightly actions. On release actions, it adds `tc_release`.
- `setup_logging` now uses `logging.INFO` if not `verbose`. It also reduces `botocore`, `boto3`, and `chardet` logging to `logging.INFO`.

### Removed
- Removed mozilla-aurora from `RELEASE_BRANCHES`
- Removed `push-to-staging` action

## [1.0.0] - 2017-08-28
### Added
- Changelog
- Support for partials in manifest production for downstream tasks
