#!/usr/bin/env bash

set -euxo pipefail

project_dir="$(dirname "$(dirname "$(readlink -f "$0")")")"
cd "$project_dir"

# Actual compilation
ANTIDOTE_COMPILED=true ANTIDOTE_CYTHON_OPTIONS=all python setup.py build_ext --inplace
