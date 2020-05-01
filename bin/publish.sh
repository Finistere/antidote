#!/usr/bin/env bash

set -euxo pipefail

PROJECT_DIR="$(dirname "$(dirname "$(readlink -f "$0")")")"

cd "$PROJECT_DIR"

rm -rf dist/*
rm -rf wheelhouse/*

venv_dir="/tmp/antidote-sdist"
python -m venv "$venv_dir"
"$venv_dir/bin/python" setup.py sdist
"$venv_dir/bin/pip" install dist/*
"$venv_dir/bin/pip" install -r requirements/tests.txt
"$venv_dir/bin/pytest" tests
rm -rf "$venv_dir"
bin/build-all-wheels.sh

twine upload dist/* wheelhouse/*
