# Change Log
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

# [2.1.0] - 2018-07-02
### Added
- additional validation checks are now being performed to make sure Ship-it side reflects the corresponding values after updating them

# [2.0.0] - 2018-06-28
### Removed
- support for py35 in testing

### Added
- support for 3.6 and 3.7-dev in testing
- enriched shipitscript to handle multiple behaviors (`mark-as-started` and `mark-as-shipped`)
- add coveragerc file
- add badge for Build / Travis in README

# [1.0.0] - 2018-03-16
### Changed
- `script.async_main()` relies on scriptworker (>= 10.2.0) to:
  - initialize context, config, and task
  - validate the task schema

### Removed
- `exceptions.TaskVerificationError` in favor of the one in scriptworker
- `script.usage()` now handled by scriptworker
- `task.validate_task_schema()` now handled by scriptworker


# [0.1.0] - 2018-01-31
Initial release
