# Prefixes
Supported scope prefixes:
* `project:releng:beetmover`
  * Used for Firefox/Fennec/Devedition style beetmover tasks

* `project:comm:thunderbird:releng:beetmover`
  * Used for Thunderbird style beetmover tasks


# Scopes
* `{scope_prefix}:action:push-to-candidates`
  * Tells beetmoverscript to copy to candidates directory in S3 the corresponding release artifacts
  * **Conflicts**: with any other `{scope_prefix}:action:*`
  * **Branch Restrictions**: `None`

* `{scope_prefix}:action:push-to-release`
  * Tells beetmoverscript to move the artifacts from candidates directory to releases directory for the corresponding release
  * **Conflicts**: with any other `{scope_prefix}:action:*`
  * **Branch Restrictions**: `None`

* `{scope_prefix}:action:push-to-nightly`
  * Tells beetmoverscript to copy to nightly directory in S3 the corresponding release artifacts
      * This is **default** if no `action` specified in scopes.
  * **Conflicts**: with any other `{scope_prefix}:action:*`
  * **Branch Restrictions**: `all-nightly-tasks`
  
* `{scope_prefix}:action:push-to-partner`
  * Tells beetmoverscript to move the corresponding artifacts of partner releases of Firefox to their corresonding private buckets
  * **Conflicts**: with any other `{scope_prefix}:action:*`
  * **Branch Restrictions**: `all-candidates-tasks`

* `{scope_prefix}:bucket:dep`
  * Tells beetmoverscript to use the dep (which stands for dependent) credentials to access the staging buckets
  * **Conflicts**: with any other `{scope_prefix}:bucket:*`
  * **Branch Restrictions**: `None`
  
* `{scope_prefix}:bucket:dep-partner`
  * Tells beetmoverscript to use the staging credentials to access the partner bucket
  * **Conflicts**: with any other `{scope_prefix}:bucket:*`
  * **Branch Restrictions**: `None`

* `{scope_prefix}:bucket:nightly`
  * Tells beetmoverscript to use the production credentials to access the nightly bucket
  * **Conflicts**: with any other `{scope_prefix}:bucket:*`
  * **Branch Restrictions**: `all-nightly-branches`
  
* `{scope_prefix}:bucket:partner`
  * Tells beetmoverscript to use the production credentials to access the partner bucket
  * **Conflicts**: with any other `{scope_prefix}:bucket:*`
  * **Branch Restrictions**: `None`

* `{scope_prefix}:bucket:release`
  * Tells beetmoverscript to use the production credentials to access the release buckets (namely candidates and releases)
  * **Conflicts**: with any other `{scope_prefix}:bucket:*`
  * **Branch Restrictions**: `all-release-branches` 
