#!/usr/bin/env bash

set -euxo pipefail

project_dir="$(dirname "$(dirname "$(readlink -f "$0")")")"

cd "$project_dir"

find src -name '*.so' -exec rm {} +
find src -name '*.cpp' -exec rm {} +
find src -name '*.pyc' -exec rm {} +
find src -name '__pycache__' -exec rm -r {} +
rm -rf build
