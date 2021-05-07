#!/bin/bash

# We need ptvsd in the root
/Applications/QGIS.app/Contents/MacOS/bin/python3 -m pip install ptvsd

virtualenv -p /Applications/QGIS.app/Contents/MacOS/bin/python3 .venv

# Install our development tools
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install pb_tool ptvsd pylint autopep8