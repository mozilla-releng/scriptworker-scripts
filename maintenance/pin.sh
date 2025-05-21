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

build_python_image() {
    local version=$1
    local tag=$2
    printf "FROM python:${version}-slim\nCOPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/" | docker build --platform linux/x86_64 --pull --tag "$tag" -
}

if [ ${#PY38_DIRS} -gt 0 ]; then
    build_python_image 3.8.3 "scriptworker-script-pin:3.8.3"
    docker run --platform linux/x86_64 --rm -t -v "$PWD":/src -e EXTRA_ARGS="$EXTRA_ARGS" -e SUFFIX=py38.txt -e PYTHON_VERSION=3.8.3 -w /src scriptworker-script-pin:3.8.3 maintenance/pin-helper.sh "${PY38_DIRS[@]}"
fi
if [ ${#PY311_DIRS} -gt 0 ]; then
    build_python_image 3.11.9 "scriptworker-script-pin:3.11.9"
    docker run --platform linux/x86_64 --rm -t -v "$PWD":/src -e EXTRA_ARGS="$EXTRA_ARGS" -e PYTHON_VERSION=3.11.9 -w /src scriptworker-script-pin:3.11.9 maintenance/pin-helper.sh "${PY311_DIRS[@]}"
fi
