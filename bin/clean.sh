#!/usr/bin/env bash

set -euxo pipefail

project_dir="$(dirname "$(dirname "$(readlink -f "$0")")")"

cd "$project_dir"

find src tests -name '*.so' -exec rm {} +
find src tests -name '*.cpp' -exec rm {} +
find src tests -name '*.pyc' -exec rm {} +
find src tests -name '__pycache__' -exec rm -r {} +
rm -rf build
