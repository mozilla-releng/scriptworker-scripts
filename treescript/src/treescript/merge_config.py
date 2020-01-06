"""Configuration for repository merges."""

NEW_ESR_BRANCH = "esr68"

merge_configs = {
    "central_to_beta": {
        "version_files": ["browser/config/version.txt", "config/milestone.txt"],
        "version_files_suffix": ["browser/config/version_display.txt"],
        "version_suffix": "b1",
        "copy_files": [],
        "replacements": [
            # File, from, to
            (f, "ac_add_options --with-branding=browser/branding/nightly", "ac_add_options --enable-official-branding")
            for f in [
                "browser/config/mozconfigs/linux32/l10n-mozconfig",
                "browser/config/mozconfigs/linux64/l10n-mozconfig",
                "browser/config/mozconfigs/win32/l10n-mozconfig",
                "browser/config/mozconfigs/win64/l10n-mozconfig",
                "browser/config/mozconfigs/win64-aarch64/l10n-mozconfig",
                "browser/config/mozconfigs/macosx64/l10n-mozconfig",
            ]
        ]
        + [
            # File, from, to
            ("build/mozconfig.common", "MOZ_REQUIRE_SIGNING=${MOZ_REQUIRE_SIGNING-0}", "MOZ_REQUIRE_SIGNING=${MOZ_REQUIRE_SIGNING-1}"),
            (
                "build/mozconfig.common",
                "# Disable enforcing that add-ons are signed by the trusted root",
                "# Enable enforcing that add-ons are signed by the trusted root",
            ),
        ],
        "from_branch": "central",
        "to_branch": "beta",
        "push_repositories": {"from": "https://hg.mozilla.org/mozilla-central", "to": "https://hg.mozilla.org/releases/mozilla-beta"},
        "require_debugsetparents": True,
        "base_tag": "FIREFOX_BETA_{major_version}_BASE",
        "end_tag": "FIREFOX_BETA_{major_version}_END",
    },
    "beta_to_release": {
        "version_files": [],
        "version_suffix": "",
        "copy_files": [{"src": "browser/config/version.txt", "dst": "browser/config/version_display.txt"}],
        "replacements": [
            # File, from, to
        ],
        "from_branch": "beta",
        "to_branch": "release",
        "push_repositories": {"from": "https://hg.mozilla.org/releases/mozilla-beta", "to": "https://hg.mozilla.org/releases/mozilla-release"},
        "require_debugsetparents": True,
        "base_tag": "FIREFOX_RELEASE_{major_version}_BASE",
        "end_tag": "FIREFOX_RELEASE_{major_version}_END",
        "require_remove_locales": False,
    },
    "release_to_esr": {
        "version_files_suffix": ["browser/config/version_display.txt"],
        "version_suffix": "esr",
        "copy_files": [],
        "replacements": [
            # File, from, to
            (
                "build/mozconfig.common",
                "# Enable enforcing that add-ons are signed by the trusted root",
                "# Disable enforcing that add-ons are signed by the trusted root",
            ),
            ("build/mozconfig.common", "MOZ_REQUIRE_SIGNING=${MOZ_REQUIRE_SIGNING-1}", "MOZ_REQUIRE_SIGNING=${MOZ_REQUIRE_SIGNING-0}"),
        ],
        # Pull from ESR repo, since we have already branched it and have landed esr-specific patches on it
        # We will need to manually merge mozilla-release into before runnning this.
        "from_branch": NEW_ESR_BRANCH,
        "to_branch": NEW_ESR_BRANCH,
        "require_debugsetparents": False,
        "base_tag": "FIREFOX_ESR_{major_version}_BASE",
        "require_remove_locales": False,
        "requires_head_merge": False,
    },
}
