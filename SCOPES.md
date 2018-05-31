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

* `{scope_prefix}:format:gpg`
  * Tells signingscript to expect to use the `gpg` signing format on some or all of the upstreamArtifacts.
  * **Branch Restrictions**: `None`

* `{scope_prefix}:format:jar`
  * Tells signingscript to expect to use the `jar` signing format on some or all of the upstreamArtifacts.
  * **Branch Restrictions**: `None`

* `{scope_prefix}:format:focus-jar`
  * Tells signingscript to expect to use the `focus-jar` signing format on some or all of the upstreamArtifacts.
  * **Branch Restrictions**: `None`

* `{scope_prefix}:format:macapp`
  * Tells signingscript to expect to use the `macapp` signing format on some or all of the upstreamArtifacts.
  * **Branch Restrictions**: `None`

* `{scope_prefix}:format:osslsigncode`
  * Tells signingscript to expect to use the `osslsigncode` signing format on some or all of the upstreamArtifacts.
  * **Branch Restrictions**: `None`

* `{scope_prefix}:format:sha2signcode`
  * Tells signingscript to expect to use the `sha2signcode` signing format on some or all of the upstreamArtifacts.
  * **Branch Restrictions**: `None`

* `{scope_prefix}:format:sha2signcodestub`
  * Tells signingscript to expect to use the `sha2signcodestub` signing format on some or all of the upstreamArtifacts.
  * **Branch Restrictions**: `None`

* `{scope_prefix}:format:signcode`
  * Tells signingscript to expect to use the `signcode` signing format on some or all of the upstreamArtifacts.
  * **Branch Restrictions**: `None`

* `{scope_prefix}:format:widevine`
  * Tells signingscript to expect to use the `widevine` signing format on some or all of the upstreamArtifacts.
  * **Branch Restrictions**: `None`

* `{scope_prefix}:format:widevine_blessed`
  * Tells signingscript to expect to use the `widevine_blessed` signing format on some or all of the upstreamArtifacts.
  * **Branch Restrictions**: `None`

* `{scope_prefix}:format:*`
  * Where * is not in the above format:* set
  * Tells signingscript to expect to use basic `sign_file` signing format on some or all of the upstreamArtifacts.
  * **Branch Restrictions**: `None`
