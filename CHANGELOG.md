# Change Log
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

# 0.5.0
* `script.async_main()` relies on scriptworker (>= 10.2.0) to:
 * initialize context, config, and task
 * validate the task schema
 * `exceptions.TaskVerificationError` in favor of the one in scriptworker
 * `script.usage()` now handled by scriptworker
 * `task.validate_task_schema()` now handled by scriptworker

* Now that Firefox 59 is on release:
 * `dry_run` is not accepted anymore in task payload
 * strings aren't fetched anymore by this worker type

# 0.4.1
* Google Play strings are now optionally fetched from an upstream task.

# 0.4.0
* Deprecated `payload.dry_run` in favor of `payload.commit` in task definition
* Add support of dep-signing. dep-signing is used by testing APKs. pushapkscript won't make a single request to Google Play if such APK is detected.

# 0.3.4
* APK verification now includes a pass on the digest algorithm

# 0.3.3
Add FAQ
Dawn project: Allow "aurora" scope to be still used in task definition
Support different architectures depending on which channel we are

## 0.3.2
Fix task validation which refused a payload with `dry_run` in it

## 0.3.1
Tasks can now define a rollout percentage for the rollout track

## 0.3.0
* Artifacts are downloaded thanks to Chain of Trust
* APK architectures don't need to be manually input. They are now automatically detected.

## 0.2.2
Pin dependencies in Puppet only.
Use new tc-migrated build locations.

## 0.2.1
Upgrade to scriptworker v2.0.0 (without Chain of Trust), which reports errors back to Treeherer.

## 0.2.0
Upgrade to scriptworker v1.0.0b7 (without Chain of Trust). Please update your config accordingly to the new config_example.json

## 0.1.4
Mute debug logs of oauth2client

## 0.1.3
APKs are not committed onto Google Play Store, by default anymore.

## 0.1.2
Use scriptworker 0.7.2 which notably fixes how message_info['task_info'] is used.  A new property called "hintId" broke a function call.

## 0.1.1
Fix package missing files

## 0.1.0
Initial release
