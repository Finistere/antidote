#!/usr/bin/env bash

set -euxo pipefail

PROJECT_DIR="$(dirname "$(dirname "$(readlink -f "$0")")")"

cd "$PROJECT_DIR"

# Clean-up
find src -name '*.so' -exec rm {} +
find src -name '*.cpp' -exec rm {} +
rm -rf build

# Actual compilation
ANTIDOTE_COMPILED=true python setup.py build_ext --inplace
