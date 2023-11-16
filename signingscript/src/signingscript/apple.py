import logging
import os
from shutil import copy2

from signingscript.exceptions import SigningScriptError

log = logging.getLogger(__name__)


PROVISIONING_PROFILE_FILENAMES = {
    "firefox": "orgmozillafirefox.provisionprofile",
    "devedition": "orgmozillafirefoxdeveloperedition.provisionprofile",
    "nightly": "orgmozillanightly.provisionprofile",
}


def copy_provisioning_profiles(bundlepath, configs):
    """Copy provisioning profiles inside bundle
    Args:
        bundlepath (str): The absolute path to the app bundle
        configs (list): The list of configs with schema [{"profile_name": str, "target_path": str}]
    """
    for cfg in configs:
        profile_name = cfg.get("profile_name")
        target_path = cfg.get("target_path")
        if not profile_name or not target_path:
            raise SigningScriptError(f"profile_name and target_path are required. Got: {cfg}")

        if profile_name not in PROVISIONING_PROFILE_FILENAMES.values():
            raise SigningScriptError(f"profile_name not allowed: {profile_name}")

        profile_path = os.path.join(os.path.dirname(__file__), "data", profile_name)
        if not os.path.exists(profile_path):
            raise SigningScriptError(f"Provisioning profile not found: {profile_name}")

        # Resolve absolute destination path
        target_abs_path = os.path.join(bundlepath, target_path if target_path[0] != "/" else target_path[1:])
        if os.path.exists(target_abs_path):
            log.warning("Provisioning profile at {target_path} already exists, overriding.")

        log.info(f"Copying {profile_name} to {target_abs_path}")
        copy2(profile_path, target_abs_path)
