# Change Log
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

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
