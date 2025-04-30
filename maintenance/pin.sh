#!/bin/bash
set -e

EXTRA_ARGS=${EXTRA_ARGS:-""}

if [ $# -gt 0 ]; then
    read -r -a DIRS <<< "$@"
else
    DIRS=(
        addonscript
        balrogscript
        beetmoverscript
        bitrisescript
        bouncerscript
        configloader
        githubscript
        iscript
        landoscript
        notarization_poller
        pushapkscript
        pushflatpakscript
        pushmsixscript
        scriptworker_client
        shipitscript
        signingscript
        treescript
        .
    )
fi

# Note: some "scripts" have to be compiled for both python versions
PY_38_SCRIPTS=(
    configloader
    scriptworker_client
    iscript
    notarization_poller
)
PY_311_SCRIPTS=(
    addonscript
    balrogscript
    beetmoverscript
    bitrisescript
    bouncerscript
    configloader
    githubscript
    landoscript
    pushapkscript
    pushflatpakscript
    pushmsixscript
    scriptworker_client
    shipitscript
    signingscript
    treescript
    .
)

# Create a list of directories that need to be compiled for each python version
PY38_DIRS=()
PY311_DIRS=()
for idx in "${!DIRS[@]}"; do
    for script in "${PY_38_SCRIPTS[@]}"; do
        if [[ "${DIRS[$idx]}" == "$script" ]]; then
            PY38_DIRS+=("${DIRS[$idx]}")
        fi
    done
    for script in "${PY_311_SCRIPTS[@]}"; do
        if [[ "${DIRS[$idx]}" == "$script" ]]; then
            PY311_DIRS+=("${DIRS[$idx]}")
        fi
    done
done

INSTALLED_PYTHON_VERSIONS=$(uv python list)
check_python_version() {
    local version=$1
    if ! echo $INSTALLED_PYTHON_VERSIONS | grep -q "$version"; then
        echo "ERROR: Python $version is not installed. Hint: run 'uv python install $version'. If you are using a virtualenv, make sure to activate it first."
        exit 1
    fi
}

if [ ${#PY38_DIRS} -gt 0 ]; then
    # Make sure python 3.8 is installed
    # This is the version used in the old mac signers, once the new signers are in place, we can remove this
    # and just use python 3.11 for everything
    check_python_version 3.8
    PYTHON_VERSION=3.8 SUFFIX=py38.txt maintenance/pin-helper.sh "${PY38_DIRS[@]}"
fi
if [ ${#PY311_DIRS} -gt 0 ]; then
    # Make sure python 3.11 is installed
    check_python_version 3.11
    PYTHON_VERSION=3.11 SUFFIX=txt maintenance/pin-helper.sh "${PY311_DIRS[@]}"
fi
