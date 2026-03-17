# Prefixes
Supported scope prefixes:
* `project:releng:flathub:firefox`
* `project:comm:thunderbird:releng:flathub`

Scopes:
* `{scope_prefix}:stable:{app_id}`: push `app_id` to flathub
* `{scope_prefix}:beta:{app_id}`: push `app_id` to flathub-beta
* `{scope_prefix}:mock:{app_id}`: don't push to flathub
* `{scope_prefix}:stable`, `{scope_prefix}:beta`, `{scope_prefix}:mock`: push the default/fallback app id
