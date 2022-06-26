#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(dirname "$(dirname "$(readlink -f "$0")")")"

rm -f "$PROJECT_DIR"/wheelhouse/* || true

# shellcheck disable=SC2043
for PLATFORM in manylinux_2_24_x86_64; do
    echo -e "\e[32mStarting $PLATFORM\e[0m"
    DOCKER_IMAGE="quay.io/pypa/$PLATFORM"
    docker pull "$DOCKER_IMAGE"
    docker run --rm -it \
        --user "$(id -u):$(id -g)"\
        -e PLATFORM="$PLATFORM" \
        -v "$PROJECT_DIR:/antidote" \
        "$DOCKER_IMAGE" \
        $(if [[ "$DOCKER_IMAGE" == "*_i686" ]]; then echo "linux32"; fi) \
        /antidote/bin/docker-build-wheels.sh
done
