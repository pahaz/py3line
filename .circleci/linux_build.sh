#!/bin/bash

set -ex

rm -rf venv

uname -a
virtualenv -p ${TOOLCHAIN_PATH}/bin/python3 venv
venv/bin/pip install pyinstaller==3.3.1
venv/bin/pyinstaller py3line.py --onefile
mv dist/py3line dist/py3line-Linux-x86_64
dist/py3line-Linux-x86_64 --version
