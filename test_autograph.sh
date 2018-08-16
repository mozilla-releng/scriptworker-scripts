#!/usr/bin/env bash

set -e

mkdir -p artifact_dir/
mkdir -p work_dir/cot/upstream-task-id1/

function usage() {
    cat <<EOF
test_autograph.sh tests signing mar files with autograph from signingscript

Takes a list of mar files urls as args:

test_autograph.sh http://ftp.mozilla.org/pub/firefox/nightly/latest-mozilla-central/firefox-63.0a1.en-US.linux-x86_64.complete.mar http://ftp.mozilla.org/pub/firefox/nightly/latest-mozilla-central/firefox-63.0a1.en-US.win64-asan-reporter.complete.mar

For each URL:

1. treats everything following the last trailing slash in the url as
the filename (e.g. firefox-63.0a1.en-US.linux-x86_64.complete.mar and
firefox-63.0a1.en-US.win64-asan-reporter.complete.mar)

2. checks if file is in the $CWD; if not, tries to fetch it as a URL

3. writes relevant config files for signingscript

4. submits the files to autograph with the dev/example autograph credentials

Requires python 3.
EOF
    exit 0
}

if [ $# -eq 0 ]
then
    usage
fi


# paths is a JSON list to inject as payload in dummy work_dir/task.json
# e.g. "firefox-mozilla-central-58.0a1-linux-x86_64-en-US-20171001220301-20171002100134.partial.mar", "firefox-mozilla-central-58.0a1-linux-x86_64-en-US-20171001220301-20171002220204.partial.mar"
paths=""
for url in $@
do
    file=$(echo -n "$url" | python -c 'print(input().split("/")[-1])')
    test -f $file || (
	wget $url && \
	cp $file work_dir/cot/upstream-task-id1/
    )
    paths="${paths}\"${file}\", "
done
paths=$(echo $paths | sed 's/,$//')

AUTOGRAPH_URL=https://autograph-hsm.dev.mozaws.net
AUTOGRAPH_HAWK_ID=alice
AUTOGRAPH_HAWK_SECRET=fs5wgcer9qj819kfptdlp8gm227ewxnzvsuj9ztycsx08hfhzu

# not using the signingserver so any example_server_config.json will do
cat <<EOF > autograph_test_server_config.json
{
    "project:releng:signing:cert:dep-signing": [
        ["${AUTOGRAPH_URL}", "${AUTOGRAPH_HAWK_ID}", "${AUTOGRAPH_HAWK_SECRET}", ["autograph_mar384"], "autograph"]
    ]
}
EOF

# config.json using autograph hsm dev config
cat <<EOF > autograph_test_config.json
{
    "signing_server_config": "autograph_test_server_config.json",
    "work_dir": "work_dir",
    "artifact_dir": "artifact_dir",
    "schema_file": "signingscript/data/signing_task_schema.json",
    "signtool": "signtool",
    "ssl_cert": "signingscript/data/host.cert",
    "taskcluster_scope_prefix": "project:releng:signing:",
    "token_duration_seconds": 1200,
    "verbose": true,
    "dmg": "dmg",
    "hfsplus": "hfsplus",
    "zipalign": "zipalign"
}
EOF

# dummy task.json
cat <<EOF > work_dir/task.json
{
  "created": "2016-05-04T23:15:17.908Z",
  "deadline": "2016-05-05T00:15:17.908Z",
  "dependencies": ["VALID_TASK_ID"],
  "expires": "2017-05-05T00:15:17.908Z",
  "extra": {},
  "metadata": {
    "description": "Markdown description of **what** this task does",
    "name": "Example Task",
    "owner": "name@example.com",
    "source": "https://tools.taskcluster.net/task-creator/"
  },
  "payload": {
    "upstreamArtifacts": [{
      "taskId": "upstream-task-id1",
      "taskType": "build",
      "paths": [
         ${paths}
      ],
      "formats": ["autograph_mar384"]
    }],
    "maxRunTime": 600
  },
  "priority": "normal",
  "provisionerId": "test-dummy-provisioner",
  "requires": "all-completed",
  "retries": 0,
  "routes": [],
  "schedulerId": "-",
  "scopes": [
    "project:releng:signing:cert:dep-signing",
    "project:releng:signing:autograph:dep-signing",
    "project:releng:signing:format:autograph_mar384"
  ],
  "tags": {},
  "taskGroupId": "CRzxWtujTYa2hOs20evVCA",
  "workerType": "dummy-worker-aki"
}
EOF

time signingscript autograph_test_config.json
# TODO: check mar is valid and signed using https://github.com/mozilla/build-mar
