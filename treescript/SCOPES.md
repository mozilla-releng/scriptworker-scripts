# Prefixes
Supported scope prefixes:
* `project:releng:treescript`
  * Used for Firefox/Fennec/Devedition style treescript tasks

* `project:comm:thunderbird:releng`
  * Used for Thunderbird style treescript tasks

# Scopes
* `{scope_prefix}:action:push`
  * Tells treescript to push the commits it created.
  * **Branch Restrictions**: `all-release-branches`

* `{scope_prefix}:action:tagging`
  * Treescript will create tags as specified in the tasks payload.
  * **Branch Restrictions**: `None`

* `{scope_prefix}:action:version_bump`
  * Treescript will perform a version bump as specified in the tasks payload.
  * **Branch Restrictions**: `None`
