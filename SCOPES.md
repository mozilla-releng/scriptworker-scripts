# Prefixes
Supported scope prefixes:
* `project:releng:treescript:action`
  * Used to tell which action(s) the treescript should perform

# Scopes
* `{scope_prefix}:push`
  * Tells treescript to push the commits it created.
  * **Branch Restrictions**: `all-release-branches`

* `{scope_prefix}:tagging`
  * Treescript will create tags as specified in the tasks payload.
  * **Branch Restrictions**: `None`

* `{scope_prefix}:version_bump`
  * Treescript will perform a version bump as specified in the tasks payload.
  * **Branch Restrictions**: `None`
