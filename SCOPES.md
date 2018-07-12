# Prefixes
Supported scope prefixes:
* `project:releng:bouncer`
  * Used for Firefox/Fennec/Devedition style bouncer tasks

* `project:comm:thunderbird:releng:bouncer`
  * Used for Thunderbird style bouncer tasks


# Scopes
* `{scope_prefix}:action:aliases`
  * Tells bouncerscript to update bouncer aliases.
  * **Conflicts**: with any other `{scope_prefix}:action:*`
  * **Branch Restrictions**: `None`

* `{scope_prefix}:action:submission`
  * Tells bouncerscript to do initial bouncer submission.
  * **Conflicts**: with any other `{scope_prefix}:action:*`
  * **Branch Restrictions**: `None`


* `{scope_prefix}:server:staging`
  * Tells bouncerscript to perform its actions against the stage server
  * **Conflicts**: with any other `{scope_prefix}:server:*`
  * **Branch Restrictions**:
    * `all-staging-branches` (For `Firefox` only)
    * `None` (For `Thunderbird` only)

* `{scope_prefix}:server:production`
  * Tells bouncerscript to perform its actions against the production server
  * **Conflicts**: with any other `{scope_prefix}:server:*`
  * **Branch Restrictions**:
    * `all-production-branches` (For `Firefox` only)
    * `all-release-branches` (For `Thunderbird` only)
