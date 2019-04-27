#!/usr/bin/env bash

set -euxo pipefail

PROJECT_DIR="$(dirname "$(dirname "$(readlink -f "$0")")")"

rm -rf "$PROJECT_DIR"/build/*

for DIR in src tests; do
    for EXTENSION in cpp so html pyc; do
        find "$PROJECT_DIR/$DIR" -name "*.$EXTENSION" -exec rm -f {} \;
    done
done