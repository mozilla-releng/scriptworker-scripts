Bouncerscript README

[![Build Status](https://travis-ci.org/mozilla-releng/bouncerscript.svg?branch=master)](https://travis-ci.org/mozilla-releng/bouncerscript)
[![Coverage Status](https://coveralls.io/repos/github/mozilla-releng/bouncerscript/badge.svg?branch=master)](https://coveralls.io/github/mozilla-releng/bouncerscript?branch=master)


## deploy a new version

1. Once your PR is reviewed and passes the tests, have one of the admins review & merge it
2. Bump to new version in `version.txt` and commit with a "%VERSION%" message
3. `git tag -s %VERSION%`
4. `git push`
5. `git push --tags`
6. Create tarball with `python setup.py sdist` and scp that file under [puppet](http://releng-puppet2.srv.releng.scl3.mozilla.com/python/packages-3.5/)
7. Wait for that file to be synchronized across all puppet instances (emails arrive to confirm that)
8. Tweak the `bouncerscript` version under [bouncerworker module](https://dxr.mozilla.org/build-central/rev/a5b360575c6f6b67b1093b81145f4700b13bd9da/puppet/modules/bouncer_scriptworker/manifests/init.pp#29) to reflect the new value
9. Push puppet bump to `default` branch, wait for tests to run and confirmation to arrive in `#releng`. Merge it to `production` after that.
10. There is currently *a single instance of* bouncerworker. `ssh` to it and run `sudo puppet agent --test` to enforce the deployment of the newest catalog. Can also wait for the cron job to run puppet to deploy new changes every 30 mins or so.

