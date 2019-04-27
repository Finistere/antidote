#!/usr/bin/env bash
# To be used in docker images: https://github.com/pypa/manylinux

set -euxo pipefail

# Install a system package required by our library
#yum install -y atlas-devel

cd /antidote
bin/clean.sh

PYTHON_VERSIONS="\
35
36
37"

# Compile wheels
while read -r PYTHON_VERSION; do
    PYBIN="/opt/python/cp$PYTHON_VERSION-cp${PYTHON_VERSION}m/bin"
    "${PYBIN}/pip" install -r requirements/bindist.txt
    "${PYBIN}/python" setup.py bdist_wheel --dist-dir /wheelhouse/
    bin/clean.sh
done <<< "$PYTHON_VERSIONS"

# Bundle external shared libraries into the wheels
for whl in /wheelhouse/*.whl; do
    auditwheel repair "$whl" --plat "$PLAT" -w wheelhouse/
done

# Install packages and test
while read -r PYTHON_VERSION; do
    PYBIN="/opt/python/cp$PYTHON_VERSION-cp${PYTHON_VERSION}m/bin"
    "${PYBIN}/pip" install -r requirements/tests.txt
    "${PYBIN}/pip" install antidote --no-index -f wheelhouse
    (cd /antidote; "${PYBIN}/pytest")
done <<< "$PYTHON_VERSIONS"