# pushapkscript

[![Build Status](https://travis-ci.org/mozilla-releng/pushapkscript.svg?branch=master)](https://travis-ci.org/mozilla-releng/pushapkscript) [![Coverage Status](https://coveralls.io/repos/github/mozilla-releng/pushapkscript/badge.svg?branch=master)](https://coveralls.io/github/mozilla-releng/pushapkscript?branch=master)

Main script that is aimed to be run with [scriptworker](https://github.com/mozilla-releng/scriptworker) (but runs perfectly fine as a standalone script). This project is a fork of [signingscript](https://github.com/mozilla-releng/signingscript). Most of the documentation from signing script applies to this project.


## Get the code


First, you need `python>=3.5.0`.

```sh
# create the virtualenv in ./venv3
virtualenv3 venv3
# activate it
. venv3/bin/activate
git clone https://github.com/mozilla-releng/pushapkscript
cd pushapkscript
pip install pushapkscript
```

Then you need to install [jarsigner](http://docs.oracle.com/javase/8/docs/technotes/tools/windows/jarsigner.html) (usually included with JDK).

### Configure

#### Jarsigner

Add the nightly certificate to the java keystore:
```sh
keytool -import -keystore ~/.keystores/mozilla-android -file pushapkscript/data/android-nightly.cer -alias nightly
```

Note: The keystore location and the certificate alias will be used in the `config.json` section

#### config.json
```sh
cp examples/config.example.json config.json
# edit it with your favorite text editor
```

There are many values to edit. Example values should give you a hint about what to provide. If not, please see [signingscript's README](https://github.com/mozilla-releng/signingscript#config-json) for more details about allowing URLs, or contact the author for other unclear areas.

#### directories and file naming

If you aren't running through scriptworker, you need to manually create the directories that `work_dir` and `artifact_dir` point to.  It's better to use new directories for these rather than cluttering and potentially overwriting an existing directory.  Once you set up scriptworker, the `work_dir` and `artifact_dir` will be regularly wiped and recreated.


### task.json

```sh
cp examples/task.example.json /path/to/work_dir
# edit it with your favorite text editor
```

Ordinarily, scriptworker would get the task definition from TaskCluster, and write it to a `task.json` in the `work_dir`.  Since you're initially not going to run through scriptworker, you need to put this file on disk yourself.

The important entries to edit are the:
 * `apks`: point to the file(s) to publish to Google Play
 * `dependencies`: need to match the `taskId`s of the URLs unless you modify the `valid_artifact_*` config items as specified above
 * `scopes`: the first and only scope, `project:releng:googleplay:*`, tells which product in Google Play store should be updated (either [aurora](https://play.google.com/store/apps/details?id=org.mozilla.fennec_aurora), [beta](https://play.google.com/store/apps/details?id=org.mozilla.firefox_beta), or [release](https://play.google.com/store/apps/details?id=org.mozilla.firefox))
 * `google_play_track`: refers to which Google Play track (either production, beta, or alpha) the APK will be uploaded

#### (aurora, beta, release) vs (alpha, beta, production)?

Google Play allows a product to have 3 different tracks (`alpha`, `beta`, `production`). Tracks are used by end-users when they want to enroll in a beta-testing program.

However, this feature wasn't out when we started publishing Fennec. This is why Fennec is registred as 3 different product: one for each regular Firefox channel (aurora, beta, release). As a consequence, here's how products/tracks should be used.

| Product | Brand name              | Track        | Notes |
| ------- | ----------------------- | ------------ | ----- |
| release | Firefox                 | `production` |       |
| beta    | Firefox Beta            | `production` |       |
| aurora  | Firefox Aurora for Developers | `beta` | production is not used to show the product is not aimed at regular users |

Note: For development purpose, aurora on the `alpha` track can also be used.

### run

You're ready to run pushapkscript!

```sh
pushapkscript CONFIG_FILE
```

where `CONFIG_FILE` is the config json you created above.

This should download the file(s) specified in the payload, check their signatures with jarsigner and publish them to Google Play Store.

### running through scriptworker

Follow the [scriptworker readme](https://github.com/mozilla-releng/scriptworker/blob/master/README.rst) to set up scriptworker, and use `["path/to/pushapkscript", "path/to/script_config.json"]` as your `task_script`.

:warning: Make sure your `work_dir` and `artifact_dir` point to the same directories between the scriptworker config and the pushapkscript config!


## Frequently asked questions

### I'd like to test out changes in pushapkscript...

#### Do I *need* to activate chain of trust for *local* development?

No. Chain of trust is used to securely download artifacts. You can bypass that step by having artifacts already on-disk. Just put the APKs in: `$work_dir/cot/$task_id/public/build/target.apk` (each APK has a different task_id). Then, you can [run pushapkscript](#run).

#### Is there a staging instance I can push my code to?

There used to be one, but it's now decommissioned. You can spawn a new instance via puppet. To do so:

1. Create a new VM instance. You can [ask for a loaner](https://bugzilla.mozilla.org/show_bug.cgi?id=1307110).
1. On the [puppet master node](https://dxr.mozilla.org/build-central/rev/e2e751bce7198d358725904a9130bbb06a26c0f9/puppet/manifests/moco-config.pp#78), [set up a user environment](https://wiki.mozilla.org/ReleaseEngineering/PuppetAgain/HowTo/Set_up_a_user_environment).
1. Add a new node to [moco-nodes.pp](https://dxr.mozilla.org/build-central/rev/e2e751bce7198d358725904a9130bbb06a26c0f9/puppet/manifests/moco-nodes.pp#1069). The config example is present in this repo at `examples/puppet-node.example.pp`.
1. Activate chain of trust [by creating the gpg keys and whitelisting them](http://scriptworker.readthedocs.io/en/latest/chain_of_trust.html#gpg-key-management). Otherwise, artifacts won't be downloaded.
1. Edit your tasks to point to a different worker-type. Define it at your will. Please do not use the `dep` pool because it's used outside of releng, in `try` for example.
1. On your VM, make the slave [take the config of your user environment](https://wiki.mozilla.org/ReleaseEngineering/PuppetAgain/HowTo/Set_up_a_user_environment#On_the_slave_node.28s.29).

:warning: Like [explained below](#is-there-an-instance-which-doesnt-interact-with-production-data), this instance will interact with the production instance of Google Play. Please make sure `"commit": false` is in your task definitions (or don't define it).

### I'd like to test out Taskcluster tasks...

#### Is there an instance which doesn't interact with production data?

Sadly, no. The Google Play documentation doesn't mention any server we can plug to. This means, you will interact with production data. There are ways to [mitigate the risk](#how-can-i-avoid-to-publish-to-actual-users), though.

#### How can I avoid to publish to actual users?

There are 3 incremental ways to avoid targetting real users (or the entire user base):

##### 1. Use `"commit": false` in your task definition.

This will execute every step implemented in pushapkscript, but the last one, which commits the transaction to the Play store.

This allows to publish the same APK several times.

However, there are a few final checks that Google Play does only when the transaction is committed. We have already experienced one: the integrity of l10n stores (descriptions and "what's new" sections) is verified only at this time. We may extrapolate the behavior to: everything that can be done in several calls to Google Play will be checked at commit time.

If not defined in the task payload, `commit` defaults to `false`.

##### 2. Push to a closed alpha track

At some point, you may want to publish your APK anyway.

Google Play provides the ability to have [a beta and alpha program](https://support.google.com/googleplay/android-developer/answer/3131213) within a product. Aurora already uses [the beta program](#aurora-beta-release-vs-alpha-beta-production).

You can ask release management to set up a closed alpha testing on the [Google Play console](https://play.google.com/apps/publish) (Go to Release management -> App releases -> Manage Alpha) and target users by email address. Then, edit your task definition to contain `"google_play_track": "alpha"`.

###### Before going further: tear down the alpha track

:warning: Once you're done with the alpha track, you **must** ask Release Management to close it. Google Play doesn't accept another track to have more recent version, than the alpha one. If you start using another track (without closing alpha), you may end up with the following error:

```
HttpError 403 when requesting https://www.googleapis.com/androidpublisher/v2/applications/org.mozilla.fennec_aurora/edits/17791185193608549142:commit?alt=json returned "Version 2015491409 of this app can not be downloaded by any devices as they will all receive APKs with higher version codes.
```

In the case where Release Management isn't connect, there's a temporary workaround:

1. Publish the APKs on the alpha track.
1. On the Google Play dashboard, promote the APKs to the beta (then the rollout channel). Reuploading the same APKs to the beta track won't be accepted by Google Play, because APKs can only be pushed once.

##### 3. For non-aurora products: Push to the rollout track

If you are confident enough to publish to percentage of our user base, you can use [the rollout track](https://support.google.com/googleplay/android-developer/answer/6346149). Just edit your task definition to contain:
```json
"google_play_track": "rollout",
"rollout_percentage": 10,
```
if you want to target 10% of the production user base.
