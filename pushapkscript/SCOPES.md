# Prefixes
Supported scope prefixes:
* `project:releng:googleplay`
  * Used to tell which Google Play store a given apk should update.

# Scopes
* `{scope_prefix}:aurora`
  * Updates to the [*aurora*](https://play.google.com/store/apps/details?id=org.mozilla.fennec_aurora) store.
  * **Conflicts**: with any other `{scope_prefix}:*`
  * **Branch Restrictions**:
    * `nightly`

* `{scope_prefix}:beta`
  * Updates to the [*beta*](https://play.google.com/store/apps/details?id=org.mozilla.firefox_beta) store
  * **Conflicts**: with any other `{scope_prefix}:*`
  * **Branch Restrictions**:
    * `beta`

* `{scope_prefix}:release`
  * Updates to the [*release*](https://play.google.com/store/apps/details?id=org.mozilla.firefox) store
  * **Conflicts**: with any other `{scope_prefix}:*`
  * **Branch Restrictions**:
    * `release`
