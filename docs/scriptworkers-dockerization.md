# Dockerization of scriptworkers

Every scriptworker has its own `Dockerfile` in the root directory. The commands
are limited to the version used in Taskcluster and may not support newer
features. The file is kept simple and most of the logic is handled by files in
the `docker.d` directory.

- `docker.d/init.sh`

  This file contains logic that is the same for all workers and supposed to be
  identical.

- `docker.d/init_worker.sh`

  This file contains logic that is worker specific.

Both init files explicitly use shell's `test` to check for all required
environment variables in order to fail as soon as possible.

- `docker.d/scriptworker.yml` and `docker.d/worker.yml`

  These files are JSON-e templates for scriptworker and the implementation
  script. The final configs are generated during the initial boot process.
