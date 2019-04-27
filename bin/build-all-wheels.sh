#!/usr/bin/env bash

set -euxo pipefail

PROJECT_DIR="$(dirname "$(dirname "$(readlink -f "$0")")")"

rm -f "$PROJECT_DIR/wheelhouse/*" || true

MANY_LINUX_DOCKER_IMAGES="\
manylinux1_i686
manylinux1_x86_64
manylinux2010_x86_64"

while read -r DOCKER_IMAGE; do
    docker run \
        --rm -t \
        -e PLAT="$DOCKER_IMAGE" \
        -v "$PROJECT_DIR:/antidote" \
        "quay.io/pypa/$DOCKER_IMAGE" \
        $(if [ "$DOCKER_IMAGE" = "manylinux1_i686" ]; then echo "linux32"; fi) \
        /antidote/bin/docker-build-wheels.sh
done <<< "$MANY_LINUX_DOCKER_IMAGES"
