set -e
set -x

EXTRA_ARGS=${EXTRA_ARGS:-""}

if [ $# -gt 0 ]; then
    DIRS=( $@ )
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
PY_39_SCRIPTS=(
    configloader
    pushapkscript
    pushmsixscript
    scriptworker_client
    shipitscript
    signingscript
    treescript
    .
)
PY_311_SCRIPTS=(
    addonscript
    balrogscript
    beetmoverscript
    bitrisescript
    bouncerscript
    githubscript
    pushflatpakscript
)

RUNCMD="RUN apt-get update && \
    apt-get install -y \
        gir1.2-ostree-1.0 \
        libgirepository1.0-dev \
        libsodium-dev && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --upgrade pip && \
    pip install pip-compile-multi
"


PY38_DIRS=()
PY39_DIRS=()
PY311_DIRS=()
for idx in "${!DIRS[@]}"; do
    if [[ ${PY_38_SCRIPTS[@]} =~ "${DIRS[$idx]}" ]]; then
        PY38_DIRS+=("${DIRS[$idx]}")
    fi
    if [[ ${PY_39_SCRIPTS[@]} =~ "${DIRS[$idx]}" ]]; then
        PY39_DIRS+=("${DIRS[$idx]}")
    fi
    if [[ ${PY_311_SCRIPTS[@]} =~ "${DIRS[$idx]}" ]]; then
        PY311_DIRS+=("${DIRS[$idx]}")
    fi
done

if [ ${#PY38_DIRS} -gt 0 ]; then
    printf "FROM python:3.8\n${RUNCMD}" | docker build --platform linux/x86_64 --pull --tag "scriptworker-script-pin:3.8" -
    echo "${PY38_DIRS[@]}" | xargs -n8 -P8 time docker run --platform linux/x86_64 --rm -t -v "$PWD":/src -e EXTRA_ARGS="$EXTRA_ARGS" -e SUFFIX=py38.txt -w /src scriptworker-script-pin:3.8 maintenance/pin-helper.sh
fi
if [ ${#PY39_DIRS} -gt 0 ]; then
    printf "FROM python:3.9\n${RUNCMD}" | docker build --platform linux/x86_64 --pull --tag "scriptworker-script-pin:3.9" -
    echo "${PY39_DIRS[@]}" | xargs -n8 -P8 time docker run --platform linux/x86_64 --rm -t -v "$PWD":/src -e EXTRA_ARGS="$EXTRA_ARGS" -w /src scriptworker-script-pin:3.9 maintenance/pin-helper.sh
fi
if [ ${#PY311_DIRS} -gt 0 ]; then
    printf "FROM python:3.11\n${RUNCMD}" | docker build --platform linux/x86_64 --pull --tag "scriptworker-script-pin:3.11" -
    echo "${PY311_DIRS[@]}" | xargs -n8 -P8 time docker run --platform linux/x86_64 --rm -t -v "$PWD":/src -e EXTRA_ARGS="$EXTRA_ARGS" -w /src scriptworker-script-pin:3.11 maintenance/pin-helper.sh
fi
