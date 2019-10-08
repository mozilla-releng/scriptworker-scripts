[![Build Status](https://travis-ci.org/mozilla-releng/bouncerscript.svg?branch=master)](https://travis-ci.org/mozilla-releng/bouncerscript)
[![Coverage Status](https://coveralls.io/repos/github/mozilla-releng/bouncerscript/badge.svg?branch=master)](https://coveralls.io/github/mozilla-releng/bouncerscript?branch=master)


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

## Bouncer behaviors in a nutshell

Within RelEng, there are currently three types of interactions with bouncer.

### Release submission

This step is required for all types of in-tree gecko-based releases. What this
means specifically is letting bouncer know that there are new products incoming.
Keep in mind that bouncer database is consumed by Mozilla's official
[downloads](https://download.mozilla.org/) page to serve all types of
installers. Amongst those there are the main installers for new users (e.g. `exe`, `dmg`, etc)
but also the updates that are queried from Balrog. Bouncer must know of all these
artifacts' existence in order to serve them.

For example, whenever we build a (e.g.)`Firefox beta X` release,
bouncer must first know what the associated products are for this particular release.
Those could include but are not limited to the following:

1. `X-Complete`
1. `X-Partial-Y`
1. `X-Partial-Z`
1. `X-Partial-T`
1. `X-SSL`
1. `X-stub`
1. ... (where `Y`, `Z` and `T` are previous versions used for partials).


While the `SSL` files are going to be served in the downloads page for consumers,
the rest of the artifacts are going to be queried from Balrog in urls like [this](http://download.mozilla.org/?product=firefox-99.0b70-partial-99.0b69&os=%OS_BOUNCER%&lang=%LOCALE%).

To conclude, bouncer needs to have in its database all of these products.

Within release promotion, this step is called `release-bouncer-submission` and
it happens within the `promotion` phase and is among the first tasks that run.
All of the above are **separate** products from bouncer's standpoint, each
defined with its own entry, set of locales, properties and such. And each of the
products is then **associated** with certain *locations* on where to retrieve those
files from S3.

`bouncer_submission` behavior in bouncerscript handles this behavior and consists
of two operations:

* submit each of these `products` as entities in bouncer database
* submit associated `locations` for each of these products

For example, the specific `Firefox-63.0b9-Complete` **product** in bouncer looks something like:
![this](/media/Firefox-63.0b9-Complete.png?raw=true)

while its associated **locations** look something like:

![this](/media/Firefox-64.0b3_locations.png?raw=true)


### Release aliases

This step is required for all types of in-tree gecko-based releases. What this
means specifically is giving bouncer a shortcut way to point to most recent releases
for a particular channel/product. The aliases address solely the main installers that
new users are supposed to download, unpack and install their Mozilla products with. (e.g. `exe`, `dmg`, etc)

Simply stating the bouncer aliases, these are nothing more than a mapping
that associates a particular `alias` to the latest `product` that has been shipped and approved by RelEng, RelMan
and QA for that particular channel.

Within release promotion, this step is called `release-bouncer-aliases` and
it happens within the `ship` phase.

`bouncer_aliases` behavior in bouncerscript handles this behavior and consists
of one simple operation:

* update each `alias` with the corresponding latest `product`

For example, a subset of aliases looks something like:

![this](/media/aliases.png?raw=true)


### Locations

The aforementioned aliases are particularly useful to serve the installers on
the release channel, but what happens on `mozilla-central`? On trunk we don't have
multiple phases within a release, nor we have QA. We ship as soon as we build, sign,
transfer to `S3` and serve updates. For that particular reason, historically, there
have been added a couple of `products` (at first glance, they can be confused over
as being `aliases` but they are not! they are simply `products` as explained above).

Basically the following `products` have been added, each with its own set of locales,
properties and such, in the same way `bouncer_submission` automates things per release.
The only difference is that these were added only once, at one time in the past
and have just been updated ever since.
1. `firefox-nightly-latest`
1. `firefox-nightly-latest-ssl`
1. `firefox-nightly-latest-l10n`
1. `firefox-nightly-latest-l10n-ssl`

Once the products have manually been added, for each of these products, a location per
platform has been added to point to the installers's `S3` finding. Since
nightlies are served from the `latest` directories, these entries have been mostly the same
for years. With one particular exception that is the version we shipped. Every 6-8 weeks,
as part of the mergeduty, we used to bump the version for each of these locations
for each of these products. That's been fully automated recently and runs as part of
the nightly graphs every day.

`bouncer_locations` behavior in bouncerscript handles this behavior and consists
of one simple operation:

* for each of the aforementioned `products`, update each `location` by bumping its version

For example, updating all locations for one of the products looks something like:

![this](/media/nightly_locations.png?raw=true)
