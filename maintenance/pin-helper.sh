#!/bin/bash
# This runs in docker to pin our requirements files.
set -e
SUFFIX=${SUFFIX:-txt}
PYTHON_VERSION=${PYTHON_VERSION:-3.11}
EXTRA_ARGS=${EXTRA_ARGS:-""}

if [ $# -gt 0 ]; then
    read -r -a DIRS <<< "$@"
else
    echo "Usage: pin-helper.sh [script(s)]"
    exit 1
fi

for dir in "${DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "Directory $dir does not exist"
        exit 1
    fi
    if [ ! -d "$dir/requirements" ]; then
        echo "Directory $dir/requirements does not exist"
        exit 1
    fi

    pushd "$dir" > /dev/null

    case "$dir" in
        scriptworker_client)
            REQ_FILES=(base test)
            ;;
        pushflatpakscript)
            REQ_FILES=(base test local flat-manager)
            ;;
        .)
            REQ_FILES=(test docs)
            ;;
        *)
            REQ_FILES=(base test local)
            ;;
    esac

    for req_file in "${REQ_FILES[@]}"; do
        echo "$dir" "$req_file" "$SUFFIX"
        if [ ! -f "requirements/$req_file.in" ]; then
            echo "File $dir/requirements/$req_file.in does not exist"
            exit 1
        fi
        uv pip compile "requirements/$req_file.in" \
            --output-file "requirements/$req_file.$SUFFIX" \
            --python-version "$PYTHON_VERSION" \
            --universal \
            --generate-hashes > /dev/null
        chmod 644 "requirements/$req_file.$SUFFIX"
    done
    popd > /dev/null
done
