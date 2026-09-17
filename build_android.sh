#!/usr/bin/env bash
set -e
python3 -m pip install --upgrade buildozer cython
buildozer android debug
