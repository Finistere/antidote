#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(dirname "$(dirname "$(readlink -f "$0")")")"

rm -f "$PROJECT_DIR"/wheelhouse/* || true

for PLATFORM in manylinux2014_i686 manylinux2010_x86_64 manylinux2014_x86_64; do
  echo -e "\e[32mStarting $PLATFORM\e[0m"
  DOCKER_IMAGE="quay.io/pypa/$PLATFORM"
  podman pull "$DOCKER_IMAGE"
  podman run --rm -it \
    -e PLATFORM="$PLATFORM" \
    -v "$PROJECT_DIR:/antidote" \
    -v "$HOME/.cache:/root/.cache" \
    "$DOCKER_IMAGE" \
    $(if [[ "$DOCKER_IMAGE" == "*_i686" ]]; then echo "linux32"; fi) \
    /antidote/bin/docker-build-wheels.sh
done
