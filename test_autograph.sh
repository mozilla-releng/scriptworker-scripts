#!/usr/bin/env bash

## for testing autograph mar signing from signingscript

mkdir -p artifact_dir/
mkdir -p work_dir/cot/upstream-task-id1/

test -f firefox-mozilla-central-58.0a1-linux-x86_64-en-US-20171001220301-20171002220204.partial.mar || (
    wget http://ftp.mozilla.org/pub/firefox/nightly/latest-mozilla-central/firefox-mozilla-central-58.0a1-linux-x86_64-en-US-20171001220301-20171002220204.partial.mar \
	&& \
	cp firefox-mozilla-central-58.0a1-linux-x86_64-en-US-20171001220301-20171002220204.partial.mar work_dir/cot/upstream-task-id1/
)
test -f firefox-mozilla-central-58.0a1-linux-x86_64-en-US-20171001220301-20171002100134.partial.mar || (
    wget http://ftp.mozilla.org/pub/firefox/nightly/latest-mozilla-central/firefox-mozilla-central-58.0a1-linux-x86_64-en-US-20171001220301-20171002100134.partial.mar \
	&& \
	cp firefox-mozilla-central-58.0a1-linux-x86_64-en-US-20171001220301-20171002100134.partial.mar work_dir/cot/upstream-task-id1/
)

# not using the signingserver so any example_server_config.json will do
cat <<EOF > autograph_test_server_config.json
{
    "project:releng:signing:cert:dep-signing": [
        ["https://autograph-hsm.dev.mozaws.net", "alice", "fs5wgcer9qj819kfptdlp8gm227ewxnzvsuj9ztycsx08hfhzu", ["autograph_mar384"], "autograph"]
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
        "firefox-mozilla-central-58.0a1-linux-x86_64-en-US-20171001220301-20171002100134.partial.mar",
        "firefox-mozilla-central-58.0a1-linux-x86_64-en-US-20171001220301-20171002220204.partial.mar"
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

signingscript autograph_test_config.json
# TODO: check mar is valid and signed with the hsm-dev
