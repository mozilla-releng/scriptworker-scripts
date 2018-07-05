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


## deploy a new version to staging

In order to rollout a new version of bouncerscript for testing, one must roll-out a new version, deploy it within
puppet internal pypi mirrors and pin the bouncerworkers to one's environment.

1. Once your PR is ready for testing, make sure to create a new version like `<next-version>.dev0+pr<pr number>` under `version.txt`.
1. Create wheel with `python3 setup.py bdist_wheel` and scp that file under [puppet](http://releng-puppet2.srv.releng.mdc1.mozilla.com/python/packages-3.5/)
1. Login in [puppet](http://releng-puppet2.srv.releng.mdc1.mozilla.com/) and change directory in your environment (e.g. `/etc/puppet/environments/$whoami`)
1. Make sure to have the puppet repo up-to-date there
1. Tweak the `bouncerscript` version in the module's [requirements.txt](https://github.com/mozilla-releng/build-puppet/blob/master/modules/bouncer_scriptworker/files/requirements.txt#L6) to reflect the new value,
and also to force all the dev bouncerworkers to be chained to your environment. Something like this:
```diff
diff --git a/manifests/moco-nodes.pp b/manifests/moco-nodes.pp
index a8357fb..1982cec 100644
--- a/manifests/moco-nodes.pp
+++ b/manifests/moco-nodes.pp
@@ -977,7 +977,7 @@ node /^bouncerworker-dev.*\.srv\.releng\..*\.mozilla\.com$/ {
     $only_user_ssh       = true
+    $pin_puppet_server = 'releng-puppet2.srv.releng.mdc1.mozilla.com'
+    $pin_puppet_env    = 'mtabara'
     include toplevel::server::bouncerscriptworker
 }

diff --git a/modules/bouncer_scriptworker/files/requirements.txt b/modules/bouncer_scriptworker/files/requirements.txt
--- a/modules/bouncer_scriptworker/files/requirements.txt
+++ b/modules/bouncer_scriptworker/files/requirements.txt
@@ -5,7 +5,7 @@ aiohttp==3.2.1
 PyYAML==3.12
 aiohttp==3.3.2
 arrow==0.12.1
 async_timeout==3.0.0
-bouncerscript==2.0.0  # puppet: nodownload
+bouncerscript==X.X.X # dev version to be tested
+bouncerscript==XXX
 attrs==18.1.0
 certifi==2018.4.16
...
```
1. Login to all machines to chain them to your environment and also deploy the newer testing version
```
# vpn
for i in {1..10}; do
nslookup bouncerworker-dev$i | grep Name: | sed -e 's/Name:\t//'
done > /src/ops/hosts/bouncer-dev
csshX --hosts /src/ops/hosts/bouncer-dev
sudo puppet agent --test --server=releng-puppet2.srv.releng.mdc1.mozilla.com --environment=mtabara # or unpin or w/e
```

## deploy a new version to production

1. Once your PR is reviewed and passes the tests, have one of the admins review & merge it
1. Bump to new version in `version.txt`.
1. Amend the `CHANGELOG.md` to reflect the new changes
1. Commit with a "%VERSION%" message
1. `git tag -s %VERSION%`
1. `git push`
1. `git push --tags`
1. Create wheel with `python3 setup.py bdist_wheel` and scp that file under [puppet](http://releng-puppet2.srv.releng.mdc1.mozilla.com/python/packages-3.5/)
1. Wait for that file to be synchronized across all puppet instances (emails arrive to confirm that)
1. Tweak the `bouncerscript` version in the module's [requirements.txt](https://github.com/mozilla-releng/build-puppet/blob/master/modules/bouncer_scriptworker/files/requirements.txt#L6) to reflect the new value
1. Create a PR for your change and get review
1. Merge it when approved and tests pass
1. There are currently a single prod and a single dev bouncerworkers. You can wait for the cron job to run puppet to deploy new changes every 30 mins or so. Alternatively, can wait for the puppet masters to sync the change (~5 minutes, see mail again), and force the puppet run by logging-in to each of the machines:
```
# vpn
for i in {1..10}; do
nslookup bouncerworker-$i | grep Name: | sed -e 's/Name:\t//'
done > /src/ops/hosts/bouncer-prod
csshX --hosts /src/ops/hosts/bouncer-prod
sudo puppet agent --test
```
