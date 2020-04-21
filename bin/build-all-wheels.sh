#!/usr/bin/env bash

set -euxo pipefail

PROJECT_DIR="$(dirname "$(dirname "$(readlink -f "$0")")")"

rm -f "$PROJECT_DIR/wheelhouse/*" || true

PLATFORMS="manylinux2014_i686
manylinux2014_x86_64"


for PLATFORM in $PLATFORMS; do
  DOCKER_IMAGE="quay.io/pypa/$PLATFORM"
  docker pull "$DOCKER_IMAGE"
  docker run --rm -it \
    -e PLAT="$PLATFORM" \
    -v "$PROJECT_DIR:/antidote" \
    "$DOCKER_IMAGE" \
    $(if [[ "$DOCKER_IMAGE" == "*_i686" ]]; then echo "linux32"; fi) \
    /antidote/bin/docker-build-wheels.sh
done
