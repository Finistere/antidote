#!/usr/bin/env bash

set -euxo pipefail

project_dir="$(dirname "$(dirname "$(readlink -f "$0")")")"
cd "$project_dir"

if [[ "${INSIDE_DOCKER:-}" == "yes" ]]; then
  export ANTIDOTE_COMPILED=true
  export ANTIDOTE_CYTHON_OPTIONS=all
  venv_dir="$project_dir/.cygdb-venv"
  if [[ ! -d "$venv_dir" ]]; then
    virtualenv "$venv_dir"
    source "$venv_dir/venv/bin/activate"
    pip install -U pip setuptools wheel
    pip install cython pygments
    pip install -e "$project_dir"
    pip install -r "$project_dir/requirements/tests.txt"
  else
    source "$venv_dir/venv/bin/activate"
  fi

  bash --init-file <(printf "printf '\n%%bcygdb . -- --args python -m pytest tests%%b\n' '\e[32m' '\e[0m' ")
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