# pushmsixscript

[![Build Status](https://travis-ci.org/mozilla-releng/pushmsixscript.svg?branch=master)](https://travis-ci.org/mozilla-releng/pushmsixscript) [![Coverage Status](https://coveralls.io/repos/github/mozilla-releng/pushmsixscript/badge.svg?branch=master)](https://coveralls.io/github/mozilla-releng/pushmsixscript?branch=master)

Main script that is aimed to be run with [scriptworker](https://github.com/mozilla-releng/scriptworker) (but runs perfectly fine as a standalone script).


## Get the code


First, you need `python>=3.8.0`.

```sh
virtualenv3 venv3   # create the virtualenv in ./venv3
. venv3/bin/activate # activate it
git clone https://github.com/mozilla-releng/pushmsixscript
cd pushmsixscript
pip install -r requirements/base.txt
python setup.py develop
```

### Configure

#### config.json
```sh
cp examples/config.example.json config.json
# edit it with your favorite text editor
```

There are many values to edit. Example values should give you a hint about what to provide. If not, please see [signingscript's README](https://github.com/mozilla-releng/scriptworker-scripts/tree/master/signingscript#config-json) for more details about allowing URLs, or contact the author for other unclear areas.

#### directories and file naming

If you aren't running through scriptworker, you need to manually create the directories that `work_dir` and `artifact_dir` point to.  It's better to use new directories for these rather than cluttering and potentially overwriting an existing directory.  Once you set up scriptworker, the `work_dir` and `artifact_dir` will be regularly wiped and recreated.


### task.json

```sh
cp examples/task.example.json /path/to/work_dir/task.json
# edit it with your favorite text editor
```

Ordinarily, scriptworker would get the task definition from TaskCluster, and write it to a `task.json` in the `work_dir`.  Since you're initially not going to run through scriptworker, you need to put this file on disk yourself.

The important entries to edit are the:
 * `upstreamArtifacts`: point to the file(s) to publish to the Microsoft Store
 * `dependencies`: need to match the `taskId`s of the URLs unless you modify the `valid_artifact_*` config items as specified above
 * `scopes`: the first and only scope, `project:releng:microsoftstore:*`, tells which channel on Microsoft store should be updated. For more details about scopes. See `scopes.md`


### run

You're ready to run pushmsixscript!

```sh
pushmsixscript CONFIG_FILE
```


where `CONFIG_FILE` is the config json you created above.

### running through scriptworker

Follow the [scriptworker readme](https://github.com/mozilla-releng/scriptworker/blob/master/README.rst) to set up scriptworker, and use `["path/to/pushmsixscript", "path/to/script_config.json"]` as your `task_script`.

:warning: Make sure your `work_dir` and `artifact_dir` point to the same directories between the scriptworker config and the pushmsixscript config!


## About the Store and the Store API

The Microsoft Store is an online marketplace for Windows apps, etc. Making Firefox available on the Store provides another channel for discovery and distribution of our browser.

Apps can be manually submitted and managed through the [Microsoft Partner Center](https://partner.microsoft.com). Login credentials associated with Mozilla's Partner Center account are required to view Firefox app submissions; :dividehex provided credentials for the author in November 2021.

We upload Firefox to the Store in the [msix](https://docs.microsoft.com/en-us/windows/msix/) format. msix files uploaded to the store are unsigned (the Store signs them before publishing). Firefox builds name these unsigned msix artifacts "target.store.msix". There are currently 32-bit and 64-bit builds and both artifacts are uploaded for each Store submission.

The Store defines a REST [API](https://docs.microsoft.com/en-us/windows/uwp/monetize/using-windows-store-services) which pushmsixscript uses to create Store submissions. Documentation includes useful [examples](https://docs.microsoft.com/en-us/windows/uwp/monetize/python-code-examples-for-the-windows-store-submission-api).

The submission request data required to initiate a submission is extensive and appears to be poorly documented. This data includes numerous optional preferences as well as many required settings. Failure to provide a required setting, or any validation error will result in a failed submission. It is best to use the Partner Center to set up the application initially and manually create the first submission. Once that is complete, pushmsixscript will re-use the settings for the previous submission.

The REST API includes endpoints for uploading app updates (the actual msix files), but that API proved unreliable for the large updates required by Firefox. On Microsoft's advice, pushmsixscript instead uses the azure.storage.blob library; this approach has been trouble-free.

If any step of the submission API fails (validation error, network error, etc during submission creation, update, upload, or commit), the partial submission will appear in Partner Center in a pending state; alerts in Partner Center can be useful for diagnosing what went wrong, or what is missing. It is often possible to complete a pending submission manually in Partner Center. Alternatively, a pending submission can be deleted manually in Partner Center.

If a pending submission exists at the start of a session, pushmsixscript will fail immediately; this is the most common cause of pushmsixscript failures. The script could instead delete the pending submission and proceed, but we do not want to risk over-writing a manual submission; Release Management and Product sometimes modify our configuration in the Partner Center.

After a successful submission, including a successful commit from the API, the app submission will automatically begin certification. Certification typically takes several hours and may take up to three business days. Once certification is complete, the submission can be automatically published, or await manual publishing; the Partner Center can be used to specify publishing preferences.

On the Beta channel, Firefox beta is pushed to the Store, certified, and immediately published. On the Release channel, Firefox is pushed to the Store, certified, but not published: it is published manually in the Partner Center, where rollout percentage and other publishing parameters can also be specified. Channel-specific behavior for pushmsixscript is specified in the [taskcluster configuration] (https://searchfox.org/mozilla-central/source/taskcluster/ci/release-msix-push/kind.yml)
