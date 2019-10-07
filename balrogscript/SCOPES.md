# Prefixes
Supported scope prefixes:
* `project:releng:balrog`
  * Used for Firefox/Fennec/Devedition style balrog tasks

* `project:comm:thunderbird:releng:balrog`
  * Used for Thunderbird style balrog tasks

# Scopes
* `{scope_prefix}:action:schedule`
  * Tells balrogscript to Schedule a release to ship on balrog channel(s)
  * **Conflicts**: with any other `{scope_prefix}:action:*`
  * **Branch Restrictions**: None

* `{scope_prefix}:action:submit-locale`
  * Tells balrogscript to submit locale information for a release.
    * This is **default** if no `action` specified in scopes.
  * **Conflicts**: with any other `{scope_prefix}:action:*`
  * **Branch Restrictions**: None

* `{scope_prefix}:action:submit-toplevel`
  * Tells balrogscript to submit the initial toplevel release information.
  * **Conflicts**: with any other `{scope_prefix}:action:*`
  * **Branch Restrictions**: None

* `{scope_prefix}:server:aurora`
  * Tells balrogscript to use the aurora server config
    * See-Also [the script config in puppet](https://dxr.mozilla.org/build-central/source/puppet/modules/balrog_scriptworker/templates/script_config.json.erb)
    * *Informative*: This is production balrog, with aurora, aurora-localtest, and aurora-cdntest channels (devedition)
  * **Conflicts**: with any other `{scope_prefix}:server:*`
  * **Branch Restrictions**: `None`

* `{scope_prefix}:server:beta`
  * Tells balrogscript to use the beta server config
    * See-Also [the script config in puppet](https://dxr.mozilla.org/build-central/source/puppet/modules/balrog_scriptworker/templates/script_config.json.erb)
    * *Informative*: This is production balrog, with beta, beta-localtest, and beta-cdntest channels
  * **Conflicts**: with any other `{scope_prefix}:server:*`
  * **Branch Restrictions**: 
    * `beta`

* `{scope_prefix}:server:dep`
  * Tells balrogscript to use the dep (depend) server config
    * See-Also [the script config in puppet](https://dxr.mozilla.org/build-central/source/puppet/modules/balrog_scriptworker/templates/script_config.json.erb)
    * *Informative*: This is staging balrog, with any (otherwise valid) channel
  * **Conflicts**: with any other `{scope_prefix}:server:*`
  * **Branch Restrictions**: `None`

* `{scope_prefix}:server:esr`
  * Tells balrogscript to use the esr server config
    * See-Also [the script config in puppet](https://dxr.mozilla.org/build-central/source/puppet/modules/balrog_scriptworker/templates/script_config.json.erb)
    * *Informative*: This is production balrog, with esr, esr-localtest, and esr-cdntest channels
  * **Conflicts**: with any other `{scope_prefix}:server:*`
  * **Branch Restrictions**: 
    * `esr` 

* `{scope_prefix}:server:nightly`
  * Tells balrogscript to use the nightly server config
    * See-Also [the script config in puppet](https://dxr.mozilla.org/build-central/source/puppet/modules/balrog_scriptworker/templates/script_config.json.erb)
    * *Informative*: This is production balrog, with nightly channel
  * **Conflicts**: with any other `{scope_prefix}:server:*`
  * **Branch Restrictions**: 
    * `all-nightly-branches`

* `{scope_prefix}:server:release`
  * Tells balrogscript to use the nightly server config
    * See-Also [the script config in puppet](https://dxr.mozilla.org/build-central/source/puppet/modules/balrog_scriptworker/templates/script_config.json.erb)
    * *Informative*: This is production balrog, with release, release-localtest, and release-cdntest channels.
  * **Conflicts**: with any other `{scope_prefix}:server:*`
  * **Branch Restrictions**: 
    * `release`
