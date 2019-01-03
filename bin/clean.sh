#!/usr/bin/env bash

PROJECT_DIR="$(dirname "$(dirname "$(readlink -f "$0")")")"

for EXTENSION in cpp so html ; do
    find "$PROJECT_DIR/src" -name "*.$EXTENSION" -exec rm -f {} \;
done
