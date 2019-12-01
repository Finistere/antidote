#!/usr/bin/env bash
# To be used in docker images: https://github.com/pypa/manylinux

set -euxo pipefail

cd /antidote
bin/clean.sh

PYTHON_VERSIONS="35 36 37 38"

pybin() {
  PYTHON_VERSION="$1"
  case $PYTHON_VERSION in
  35 | 36 | 37)
    echo "/opt/python/cp$PYTHON_VERSION-cp${PYTHON_VERSION}m/bin"
    ;;
  *)
    echo "/opt/python/cp$PYTHON_VERSION-cp${PYTHON_VERSION}/bin"
    ;;
  esac
}

# Compile wheels
for PYTHON_VERSION in $PYTHON_VERSIONS; do
  PYBIN="$(pybin "$PYTHON_VERSION")"
  "${PYBIN}/pip" install -r requirements/bindist.txt
  "${PYBIN}/python" setup.py bdist_wheel --dist-dir /wheelhouse/
  bin/clean.sh
done

# Bundle external shared libraries into the wheels
for whl in /wheelhouse/*.whl; do
  auditwheel repair "$whl" --plat "$PLAT" -w wheelhouse/
done

# Install packages and test
for PYTHON_VERSION in $PYTHON_VERSIONS; do
  PYBIN="$(pybin "$PYTHON_VERSION")"
  "${PYBIN}/pip" install -r requirements/tests.txt
  "${PYBIN}/pip" install antidote --no-index -f wheelhouse
  "${PYBIN}/pytest"
done
