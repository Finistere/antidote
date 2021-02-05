#!/usr/bin/env bash
# To be used in docker images: https://github.com/pypa/manylinux

set -euo pipefail

cd /antidote
GPATH="$PATH"

VENV_DIR="/tmp/venv"
WHEELHOUSE="$(pwd)/wheelhouse"
mkdir -p "$WHEELHOUSE"

step() {
    echo -e "\e[32m\e[1m[$PLATFORM/Py$PYTHON_VERSION] \e[21m$1\e[0m"
}

big-step() {
    echo ""
    step "\e[7m$1\e[27m"
}

clean() {
    rm -rf build/*
    for DIR in src tests; do
        find "$DIR" | grep -E "(__pycache__|\.pyc$|\.pyo$|\.cpp$|\.so$|\.html$)" || true | xargs rm -rf
    done
}

pybin() {
    case $PYTHON_VERSION in
    36 | 37)
        echo "/opt/python/cp$PYTHON_VERSION-cp${PYTHON_VERSION}m/bin"
        ;;
    *)
        echo "/opt/python/cp$PYTHON_VERSION-cp${PYTHON_VERSION}/bin"
        ;;
    esac
}

export ANTIDOTE_COMPILED=true

# Compile wheels
for PYTHON_VERSION in 36 37 38 39; do
    export PYTHON_VERSION
    PATH="$(pybin "$PYTHON_VERSION"):$GPATH"
    TMP_WHEELHOUSE="/tmp/$PLATFORM/$PYTHON_VERSION"
    mkdir -p "$TMP_WHEELHOUSE"

    big-step "Compiling wheel"
    step "Cleaning workspace"
    clean
    step "Installing dependencies"
    pip install -U pip build
    step "Binary distribution"
    python -m build --wheel --outdir "$TMP_WHEELHOUSE/raw"

    big-step "Auditing wheel"
    for whl in "$TMP_WHEELHOUSE/raw"/*.whl; do
        step "Auditing \e[4m$(basename "$whl")\e[24m"
        auditwheel repair "$whl" --plat "$PLATFORM" -w "$TMP_WHEELHOUSE/audited"
    done

    big-step "Testing wheel(s)"
    for whl in "$TMP_WHEELHOUSE/audited"/*.whl; do
        step "Creating new venv"
        rm -rf "$VENV_DIR" || true
        python -m venv "$VENV_DIR"
        sed -i 's/$1/${1:-}/' "$VENV_DIR"/bin/activate
        source "$VENV_DIR"/bin/activate
        pip install -U pip setuptools wheel

        step "Installing \e[4m$(basename "$whl")\e[24m"
        pip install "$whl"
        step "Starting tests"
        pip install -r requirements/tests.txt
        pytest tests
        echo ""
        deactivate
    done

    big-step "Moving wheels to permanent wheelhouse"
    mv "$TMP_WHEELHOUSE/audited"/*.whl "$WHEELHOUSE"/
    step "Done !"
    echo ""
done
