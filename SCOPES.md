# Prefixes
Supported scope prefixes:
* `project:releng:addons.mozilla.org:server`
  * Used to tell which supported addons.mozilla.org server we should use.

# Scopes
* `{scope_prefix}:staging`
  * Tells addonscript to publish to [addons.allizom.org](https://addons.allizom.org)
  * **Conflicts**: with `{scope_prefix}:production`
  * **Branch Restrictions**: None

* `{scope_prefix}:production`
  * Tells addonscript to publish to [addons.mozilla.org](https://addons.mozilla.org)
  * **Conflicts**: with `{scope_prefix}:staging`
  * **Branch Restrictions**:
    * `all-release-branches`
