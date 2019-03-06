# Prefixes
Supported scope prefixes:
* `project:releng:ship-it`
  * Used for Firefox/Fennec/Devedition style ship-it tasks

* `project:comm:thunderbird:releng:ship-it`
  * Used for Thunderbird style ship-it tasks


# Scopes
* `{scope_prefix}:action:mark-as-shipped`
  * Tells shipitscript to update Ship-it by marking that release as `shipped`
  * **Conflicts**: with any other `{scope_prefix}:action:*`
  * **Branch Restrictions**: `None`

* `{scope_prefix}:action:mark-as-started`
  * Tells shipitscript to update Ship-it by marking that release as `started`
  * **Conflicts**: with any other `{scope_prefix}:action:*`
  * **Branch Restrictions**: `None`


* `{scope_prefix}:server:staging`
  * Tells shipitscript to perform its actions against the stage server
  * **Conflicts**: with any other `{scope_prefix}:server:*`
  * **Branch Restrictions**:
    * `all-staging-branches` (For `Firefox` only)
    * `None` (For `Thunderbird` only)

* `{scope_prefix}:server:production`
  * Tells shipitscript to perform its actions against the production server
  * **Conflicts**: with any other `{scope_prefix}:server:*`
  * **Branch Restrictions**:
    * `all-production-branches` (For `Firefox` only)
    * `all-release-branches` (For `Thunderbird` only)
