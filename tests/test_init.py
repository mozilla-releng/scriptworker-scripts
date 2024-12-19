import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from pprint import pprint
from textwrap import dedent

import pytest

here = Path(__file__).parent


# These are variables that would typically be set by cloudops-infra.
# Be careful not to add anything here that would normally be set within
# the `init.sh` or `init_worker.sh` scripts, or else the purpose of the
# test will be defeated.
CONTEXT = {
    re.compile(r"addon:.*"): {
        "JWT_USER": "user",
        "JWT_SECRET": "secret",
    },
    re.compile(r"balrog:.*"): {
        "AUTH0_CLIENT_ID": "1",
        "AUTH0_CLIENT_SECRET": "1",
    },
    re.compile(r"beetmover:.*"): {
        "DEP_ID": "1",
        "DEP_KEY": "1",
        "DEP_PARTNER_ID": "1",
        "DEP_PARTNER_KEY": "1",
        "GCS_DEP_CREDS": "1",
        "GCS_RELEASE_CREDS": "1",
        "MAVEN_ID": "1",
        "MAVEN_KEY": "1",
        "MAVEN_NIGHTLY_ID": "1",
        "MAVEN_NIGHTLY_KEY": "1",
        "NIGHTLY_ID": "1",
        "NIGHTLY_KEY": "1",
        "RELEASE_ID": "1",
        "RELEASE_KEY": "1",
        "PARTNER_ID": "1",
        "PARTNER_KEY": "1",
    },
    re.compile(r"bitrise:.*"): {
        "BITRISE_ACCESS_TOKEN_STAGING": "1",
        "BITRISE_ACCESS_TOKEN_PROD": "1",
    },
    re.compile(r"bouncer:.*"): {
        "BOUNCER_USERNAME": "1",
        "BOUNCER_PASSWORD": "1",
    },
    re.compile(r"github:.*"): {
        "GITHUB_TOKEN_WRITE_ACCESS_STAGING": "1",
        "GITHUB_TOKEN_WRITE_ACCESS_PROD": "1",
    },
    re.compile(r"pushapk:.*"): {
        "GOOGLE_CREDENTIALS_FENIX_PROD": "Zm9vYmFyCg==",
        "GOOGLE_CREDENTIALS_FIREFOX_BETA": "Zm9vYmFyCg==",
        "GOOGLE_CREDENTIALS_FIREFOX_DEP": "Zm9vYmFyCg==",
        "GOOGLE_CREDENTIALS_FIREFOX_RELEASE": "Zm9vYmFyCg==",
        "GOOGLE_CREDENTIALS_FOCUS": "Zm9vYmFyCg==",
        "GOOGLE_CREDENTIALS_MOZILLAVPN": "Zm9vYmFyCg==",
        "GOOGLE_CREDENTIALS_REFERENCE_BROWSER": "Zm9vYmFyCg==",
        "GOOGLE_SERVICE_ACCOUNT_FENIX_NIGHTLY": "Zm9vYmFyCg==",
        "GOOGLE_SERVICE_ACCOUNT_FENIX_BETA": "Zm9vYmFyCg==",
        "GOOGLE_SERVICE_ACCOUNT_FENIX_RELEASE": "Zm9vYmFyCg==",
        "GOOGLE_SERVICE_ACCOUNT_FOCUS": "Zm9vYmFyCg==",
        "GOOGLE_SERVICE_ACCOUNT_MOZILLAVPN": "Zm9vYmFyCg==",
        "GOOGLE_SERVICE_ACCOUNT_REFERENCE_BROWSER": "Zm9vYmFyCg==",
    },
    re.compile(r"pushflatpak:.*"): {
        "FLATHUB_URL": "https://flathub.example.com",
        "REPO_TOKEN_BETA": "Zm9vYmFyCg==",
        "REPO_TOKEN_STABLE": "Zm9vYmFyCg==",
    },
    re.compile(r"pushmsix:.*"): {
        "TENANT_ID": "Zm9vYmFyCg==",
        "CLIENT_ID": "Zm9vYmFyCg==",
        "CLIENT_SECRET": "Zm9vYmFyCg==",
    },
    re.compile(r"signing:.*"): {
        "WIDEVINE_CERT": "Zm9vYmFyCg==",
        "AUTOGRAPH_AUTHENTICODE_EV_PASSWORD": "1",
        "AUTOGRAPH_AUTHENTICODE_EV_USERNAME": "1",
        "AUTOGRAPH_AUTHENTICODE_SHA2_PASSWORD": "1",
        "AUTOGRAPH_AUTHENTICODE_SHA2_USERNAME": "1",
        "AUTOGRAPH_FENIX_MOZILLA_ONLINE_PASSWORD": "1",
        "AUTOGRAPH_FENIX_MOZILLA_ONLINE_USERNAME": "1",
        "AUTOGRAPH_FENIX_PASSWORD": "1",
        "AUTOGRAPH_FENIX_USERNAME": "1",
        "AUTOGRAPH_FENNEC_RELEASE_PASSWORD": "1",
        "AUTOGRAPH_FENNEC_RELEASE_USERNAME": "1",
        "AUTOGRAPH_FOCUS_PASSWORD": "1",
        "AUTOGRAPH_FOCUS_USERNAME": "1",
        "AUTOGRAPH_GPG_PASSWORD": "1",
        "AUTOGRAPH_GPG_USERNAME": "1",
        "AUTOGRAPH_LANGPACK_PASSWORD": "1",
        "AUTOGRAPH_LANGPACK_USERNAME": "1",
        "AUTOGRAPH_MAR_NIGHTLY_PASSWORD": "1",
        "AUTOGRAPH_MAR_NIGHTLY_USERNAME": "1",
        "AUTOGRAPH_MAR_PASSWORD": "1",
        "AUTOGRAPH_MAR_RELEASE_PASSWORD": "1",
        "AUTOGRAPH_MAR_RELEASE_USERNAME": "1",
        "AUTOGRAPH_MAR_USERNAME": "1",
        "AUTOGRAPH_MOZILLAVPN_ADDONS_PASSWORD": "1",
        "AUTOGRAPH_MOZILLAVPN_ADDONS_USERNAME": "1",
        "AUTOGRAPH_MOZILLAVPN_DEBSIGN_PASSWORD": "1",
        "AUTOGRAPH_MOZILLAVPN_DEBSIGN_USERNAME": "1",
        "AUTOGRAPH_MOZILLAVPN_PASSWORD": "1",
        "AUTOGRAPH_MOZILLAVPN_USERNAME": "1",
        "AUTOGRAPH_OMNIJA_PASSWORD": "1",
        "AUTOGRAPH_OMNIJA_USERNAME": "1",
        "AUTOGRAPH_REFERENCE_BROWSER_PASSWORD": "1",
        "AUTOGRAPH_REFERENCE_BROWSER_USERNAME": "1",
        "AUTOGRAPH_STAGE_AUTHENTICODE_SHA2_USERNAME": "1",
        "AUTOGRAPH_STAGE_AUTHENTICODE_SHA2_PASSWORD": "1",
        "AUTOGRAPH_STAGE_FENIX_PASSWORD": "1",
        "AUTOGRAPH_STAGE_FENIX_USERNAME": "1",
        "AUTOGRAPH_STAGE_FOCUS_PASSWORD": "1",
        "AUTOGRAPH_STAGE_FOCUS_USERNAME": "1",
        "AUTOGRAPH_STAGE_GPG_PASSWORD": "1",
        "AUTOGRAPH_STAGE_GPG_USERNAME": "1",
        "AUTOGRAPH_STAGE_LANGPACK_PASSWORD": "1",
        "AUTOGRAPH_STAGE_LANGPACK_USERNAME": "1",
        "AUTOGRAPH_STAGE_MAR_PASSWORD": "1",
        "AUTOGRAPH_STAGE_MAR_USERNAME": "1",
        "AUTOGRAPH_STAGE_MOZILLAVPN_ADDONS_PASSWORD": "1",
        "AUTOGRAPH_STAGE_MOZILLAVPN_ADDONS_USERNAME": "1",
        "AUTOGRAPH_STAGE_MOZILLAVPN_DEBSIGN_PASSWORD": "1",
        "AUTOGRAPH_STAGE_MOZILLAVPN_DEBSIGN_USERNAME": "1",
        "AUTOGRAPH_STAGE_OMNIJA_PASSWORD": "1",
        "AUTOGRAPH_STAGE_OMNIJA_USERNAME": "1",
        "AUTOGRAPH_STAGE_REFERENCE_BROWSER_USERNAME": "1",
        "AUTOGRAPH_STAGE_REFERENCE_BROWSER_PASSWORD": "1",
        "AUTOGRAPH_STAGE_WIDEVINE_PASSWORD": "1",
        "AUTOGRAPH_STAGE_WIDEVINE_USERNAME": "1",
        "AUTOGRAPH_STAGE_XPI_PASSWORD": "1",
        "AUTOGRAPH_STAGE_XPI_USERNAME": "1",
        "AUTOGRAPH_STAGE_XPI_PRIVILEGED_PASSWORD": "1",
        "AUTOGRAPH_STAGE_XPI_PRIVILEGED_USERNAME": "1",
        "AUTOGRAPH_WIDEVINE_PASSWORD": "1",
        "AUTOGRAPH_WIDEVINE_USERNAME": "1",
        "AUTOGRAPH_XPI_PRIVILEGED_PASSWORD": "1",
        "AUTOGRAPH_XPI_PRIVILEGED_USERNAME": "1",
        "AUTOGRAPH_XPI_PASSWORD": "1",
        "AUTOGRAPH_XPI_USERNAME": "1",
    },
    re.compile(r"signing:adhoc:(dev|fake-prod)"): {
        "AUTOGRAPH_XPI_PASSWORD": "1",
        "AUTOGRAPH_XPI_USERNAME": "1",
    },
    re.compile(r"tree:.*"): {
        "SSH_KEY": "Zm9vYmFyCg==",
        "SSH_USER": "user",
        "GITHUB_PRIVKEY": "Zm9vYmFyCg==",
    },
}


@pytest.fixture(scope="module")
def configloader(tmp_path_factory):
    d = tmp_path_factory.mktemp("configloader")

    cl_root = here.parent.joinpath("configloader")

    # Create a shim binary to avoid installing configloader
    # (which results in metadata issues intermittent failures).
    cl_bin = d.joinpath("bin", "configloader")
    cl_bin.parent.mkdir()
    cl_bin.write_text(
        dedent(
            f"""
            #!/usr/bin/env bash
            {sys.executable} {cl_root}/src/configloader/script.py $@
            """
        )
    )
    cl_bin.chmod(cl_bin.stat().st_mode | stat.S_IEXEC)
    return d


@pytest.fixture
def app_dir(tmp_path_factory, configloader):
    app_dir = tmp_path_factory.mktemp("app")

    # Copy the 'docker.d' directory over
    repo_root = here.parent
    shutil.copytree(repo_root.joinpath("docker.d"), app_dir.joinpath("docker.d"), dirs_exist_ok=True)

    # Symlink configloader to the expected location
    os.symlink(configloader, str(app_dir.joinpath("configloader_venv")))

    # Create a dummy scriptworker binary
    scriptworker = app_dir.joinpath("bin", "scriptworker")
    scriptworker.parent.mkdir()
    scriptworker.touch()
    st = scriptworker.stat()
    scriptworker.chmod(st.st_mode | stat.S_IEXEC)

    return app_dir


def get_expected_return_code(app, product, env):
    if app == "addon":
        if product != "firefox":
            return 1
    elif app == "balrog":
        if product not in ("firefox", "thunderbird", "xpi"):
            return 1
    elif app == "beetmover":
        if product in ("adhoc", "mobile"):
            return 1
    elif app == "bouncer":
        if product not in ("firefox", "thunderbird"):
            return 1
    elif app == "github":
        if product not in ("mobile", "xpi"):
            return 1
    elif app == "pushapk":
        if product not in ("firefox", "mobile", "mozillavpn"):
            return 1
    elif app == "pushflatpak":
        if product not in ("firefox", "thunderbird"):
            return 1
    elif app == "pushmsix":
        if product != "firefox":
            return 1
    elif app == "shipit":
        if product not in ("adhoc", "app-services", "firefox", "mobile", "mozillavpn", "thunderbird", "xpi"):
            return 1
    elif app == "tree":
        if product not in ("firefox", "mobile", "thunderbird"):
            return 1
    return 0


def generate_params():
    apps = (
        "addon",
        "balrog",
        "beetmover",
        "bouncer",
        "github",
        "pushapk",
        "pushflatpak",
        "pushmsix",
        "shipit",
        "signing",
        "tree",
    )
    products = (
        "firefox",
        "thunderbird",
        "mobile",
        "app-services",
        "glean",
        "xpi",
        "mozillavpn",
        "adhoc",
    )
    envs = (
        "prod",
        "fake-prod",
        "dev",
    )
    xfail = {
        # Add here any tests that are xfail
    }
    for app in apps:
        for product in products:
            for env in envs:
                if f"{app}-{product}-{env}" in xfail:
                    yield pytest.param(app, product, env, marks=pytest.mark.xfail)
                else:
                    yield (app, product, env)


@pytest.mark.parametrize("app,product,environment", generate_params())
def test_init_script(tmp_path, app_dir, app, product, environment):
    # Copy the app's `init_worker.sh` script into docker.d
    repo_root = here.parent
    docker_d = repo_root.joinpath(f"{app}script", "docker.d")
    shutil.copytree(docker_d, app_dir.joinpath("docker.d"), dirs_exist_ok=True)

    env = {
        "APP_DIR": str(app_dir),
        "PROJECT_NAME": app,
        "COT_PRODUCT": product,
        "ENV": environment,
        "GITHUB_OAUTH_TOKEN": "secret",
        "TASKCLUSTER_ROOT_URL": "https://tc-tests.example.com",
        "TASKCLUSTER_CLIENT_ID": "/static/test/client",
        "TASKCLUSTER_ACCESS_TOKEN": "12345",
    }

    if app == "pushapk":
        mocks = (Path(__file__).parent / "mocks").resolve()
        env["PATH"] = f"{mocks}:{os.environ.get('PATH', '')}"

    if env["ENV"] == "prod":
        env["ED25519_PRIVKEY"] = "secret"

    for k, v in CONTEXT.items():
        if re.match(k, f"{app}:{product}:{environment}"):
            env.update(v)

    pprint(env)
    proc = subprocess.run([str(app_dir.joinpath("docker.d", "init.sh"))], env=env)
    assert proc.returncode == get_expected_return_code(app, product, environment)
