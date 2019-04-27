#!/usr/bin/env bash

set -euxo pipefail

PROJECT_DIR="$(dirname "$(dirname "$(readlink -f "$0")")")"

cd "$PROJECT_DIR"

rm -rf dist/*
rm -rf wheelhouse/*

python setup.py sdist
bin/build-all-wheels.sh

twine upload dist/* wheelhouse/*
