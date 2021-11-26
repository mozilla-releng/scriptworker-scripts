# Prefixes
Supported scope prefixes:
* `project:releng:microsoftstore`
  * Used to tell which Microsoft store a given msix should update.

# Scopes
* `{scope_prefix}:release`
  * Uploads to the *release* app.
  * **Conflicts**: with any other `{scope_prefix}:*`
  * **Branch Restrictions**:
    * `release`

* `{scope_prefix}:beta`
  * Uploads to the *beta* app.
  * **Conflicts**: with any other `{scope_prefix}:*`
  * **Branch Restrictions**:
    * `beta`

* `{scope_prefix}:mock`
  * Prevents uploads to the microsoft store, useful for staging.
  * **Conflicts**: with any other `{scope_prefix}:*`
  * **Branch Restrictions**:
    * `all-staging-branches`

