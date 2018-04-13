#!/usr/bin/env bash

set -e

DIR="$( cd "$( dirname "$0" )" && pwd )"

cd ${DIR}

make doctest
make clean
make html
