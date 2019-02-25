# Prefixes
Supported scope prefixes:
* `project:releng:signing`
  * Used for Firefox/Fennec/Devedition style signing tasks

* `project:comm:thunderbird:releng:signing`
  * Used for Thunderbird style signing tasks

* `project:mobile:focus:releng:signing`
  * Used for android Firefox Focus style signing tasks

# Scopes

* `{scope_prefix}:cert:dep-signing`
  * Tells signingscript to use the *Depend* certificate for a given format.
  * **Conflicts**: with any other `{scope_prefix}:cert:*`
  * **Branch Restrictions**: None

* `{scope_prefix}:cert:nightly-signing`
  * Tells signingscript to use the *Nightly* certificate for a given format.
  * **Conflicts**: with any other `{scope_prefix}:cert:*`
  * **Branch Restrictions**:
    * `all-nightly-branches`

* `{scope_prefix}:cert:release-signing`
  * Tells signingscript to use the *Release* certificate for a given format.
  * **Conflicts**: with any other `{scope_prefix}:cert:*`
  * **Branch Restrictions**:
    * `all-release-branches`
