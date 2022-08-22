#!/usr/bin/env bash

set -euxo pipefail

project_dir="$(dirname "$(dirname "$(readlink -f "$0")")")"
cd "$project_dir"

if [[ "${INSIDE_DOCKER:-}" == "yes" ]]; then
  export ANTIDOTE_COMPILED=true
  export ANTIDOTE_CYTHON_OPTIONS=all
  export PATH="/tmp/Python/bin:$PATH"
  pip3 install -U pip setuptools wheel
  pip3 install cython pygments
  pip3 install --no-binary :all: fastrlock
  pip3 install -r "$project_dir/requirements/tests.txt"

  bash --init-file <(printf "printf '\n%%bcygdb . -- --args python3 -m pytest tests%%b\n' '\e[32m' '\e[0m' ")
else
  docker build \
		--build-arg USER_ID="$(id -u)" \
		--build-arg GROUP_ID="$(id -g)" \
		--build-arg USER_NAME="$(id -un)" \
		--build-arg HOME="/home/$(id -un)" \
		-t antidote-cygdb \
		"$project_dir/bin/docker-cygdb"
  docker run \
    --user "$(id -u):$(id -g)" \
    -v "$project_dir:/antidote" \
    -w /antidote \
    -it \
    -e INSIDE_DOCKER=yes \
    antidote-cygdb:latest \
    bash -c "/antidote/bin/cygdb.sh"
fi