# Change Log
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## 0.2.2
* Upgrade requests package

## 0.2.1
* Python 2: Fix enconding issue when uploading locales that contain non-ASCII characters

## 0.2.0
* push_apk.py first publishes listing then "what's new". This fixes unsupported locales described in [bug 1349039](https://bugzilla.mozilla.org/show_bug.cgi?id=1349039)
* get_apk.py doesn't break because files are internally renamed after being downloaded
* get_apk.py: `--clean` has been removed

## 0.1.6
* Check if version codes are correctly ordered
* en-GB is now updated like any other locale
* get_apk.py supports checksum files for Fennec >= 53.0b1

## 0.1.5
* Upgrade pyOpenSSL, in order to keep support for OpenSSL v1.1.0

## 0.1.4
* Use new store_l10n APIs
* New installation instructions for OS X
* Better logs
* Test coverage

## 0.1.3
* Mute some debug logs coming from dependencies
* Add a check to prevent single locale APKs to be pushed ([bug 1314712](https://bugzilla.mozilla.org/show_bug.cgi?id=1314712))
* Add --dry-run flag

## 0.1.2
* Fix some other missing files in package

## 0.1.1
* Fix package missing files

## 0.1.0
* Initial release
