# Prefixes
Supported scope prefixes:
* `project:releng:snapcraft`
  * Used to tell which Google Play store a given apk should update.

# Scopes
* `{scope_prefix}:firefox:beta`
  * Uploads to the *beta* snap track.
    * Uses branding "Firefox Beta"
  * **Conflicts**: with any other `{scope_prefix}:firefox:*`
  * **Branch Restrictions**:
    * `beta`

* `{scope_prefix}:firefox:candidate`
  * Uploads to the *candidate* snap track.
    * Uses branding "Firefox"
  * **Conflicts**: with any other `{scope_prefix}:firefox:*`
  * **Branch Restrictions**:
    * `release`

* `{scope_prefix}:firefox:esr`
  * Uploads to the to the esr (esr/stable) snap track.
  * **Does not seem to be used**
  * **Conflicts**: with any other `{scope_prefix}:firefox:*`
  * **Branch Restrictions**: `None`

* `{scope_prefix}:firefox:mock`
  * Prevents uploads to the snap store, useful for staging.
  * **Conflicts**: with any other `{scope_prefix}:firefox:*`
  * **Branch Restrictions**:
    * `all-staging-branches`


# Snap Track Details
Snap store allows a product to have 4 different channels (edge, beta, candidate, release).
Tracks are used by end-users when they want to enroll in a less stable version of Firefox.

Pushsnap accepts a subset of what the [Snap store allows](https://docs.snapcraft.io/reference/channels#risk-levels-meaning)
