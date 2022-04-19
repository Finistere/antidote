#!/usr/bin/env bash

set -euo pipefail

project_dir="$(dirname "$(dirname "$(readlink -f "$0")")")"
cd "$project_dir"

if [[ "${INSIDE_DOCKER:-}" == "yes" ]]; then
  venv_dir="$project_dir/.tox-venv"
  if [[ ! -d "$venv_dir" ]]; then
    python3.10 -m venv "$venv_dir"
    source "$venv_dir/bin/activate"
    pip install -r "$project_dir/requirements/dev.txt"
  else
    source "$venv_dir/bin/activate"
  fi
  tox "$@"
else
  docker run \
    --user "$(id -u):$(id -g)" \
    -v "$project_dir:/antidote" \
    -w /antidote \
    -it \
    -e INSIDE_DOCKER=yes \
    quay.io/pypa/manylinux2014_x86_64:latest \
    bash -c "/antidote/bin/tox.sh $*"
fi
