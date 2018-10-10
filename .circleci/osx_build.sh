#!/bin/bash

set -ex

TOOLCHAIN_PATH="$(realpath $(dirname $0)/../build/toolchain)"

rm -rf venv

virtualenv -p ${TOOLCHAIN_PATH}/bin/python3 venv
venv/bin/pip install pyinstaller==3.3.1
venv/bin/pyinstaller py3line.py --onefile
mv dist/py3line dist/py3line-Darwin-x86_64
dist/py3line-Darwin-x86_64 --version
