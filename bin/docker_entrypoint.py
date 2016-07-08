import json
import os
import sys
import logging
import scriptworker.worker

log = logging.getLogger(__name__)
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s",
                    stream=sys.stdout,
                    level=logging.DEBUG)

'''
Read in environment variables to create configuration json files
to be used by scriptworker and balrog submitter.
'''
# Get Taskcluster credentials for scriptworker
try:
    clientId = os.environ["TC_CLIENT_ID"]
    accessToken = os.environ["TC_ACCESS_TOKEN"]
except KeyError:
    log.fatal("Please provide Taskcluster credentials in envvar TC_CLIENT_ID and TC_ACCESS_TOKEN")
    sys.exit(1)

sw_credentials = {
    'clientId': clientId,
    'accessToken': accessToken
}

# Enable other scriptworker config to be overridden by environment variables, if prefixed with SW_ and capitalized
sw_config = {
    "provisioner_id": "test-dummy-provisioner",
    "scheduler_id": "test-dummy-scheduler",
    "worker_group": "test-dummy-workers",
    "worker_type": "dummy-worker-francis",
    "work_dir": "/app/work",
    "log_dir": "/app/log",
    "artifact_dir": "/app/artifacts",
    "artifact_expiration_hours": 24,
    "artifact_upload_timeout": 1200,
    "task_script": ["/app/py2/bin/python","/app/bin/funsize-balrog-submitter.py",
                    "--taskdef","/app/work/task.json",
                    "--verbose"],
    "task_max_timeout": 1200,
    "verbose": True,
    "poll_interval": 10,
    "reclaim_interval": 60
}

for option in sw_config:
    env_var = os.environ.get('SW_{}'.format(option.upper()))
    if not env_var:
        continue
    if env_var.isdigit():
        sw_config[option] = int(env_var)
    else:
        sw_config[option] = env_var

sw_config['credentials'] = sw_credentials

with open('config.json','w') as f:
    json.dump(sw_config, f)

scriptworker.worker.main()