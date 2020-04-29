[![Build Status](https://travis-ci.org/mozilla-releng/bouncerscript.svg?branch=master)](https://travis-ci.org/mozilla-releng/bouncerscript)
[![Coverage Status](https://coveralls.io/repos/github/mozilla-releng/bouncerscript/badge.svg?branch=master)](https://coveralls.io/github/mozilla-releng/bouncerscript?branch=master)


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
![this](/bouncerscript/media/Firefox-63.0b9-Complete.png?raw=true)

while its associated **locations** look something like:

![this](/bouncerscript/media/Firefox-64.0b3_locations.png?raw=true)


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

![this](/bouncerscript/media/aliases.png?raw=true)


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

![this](/bouncerscript/media/nightly_locations.png?raw=true)
