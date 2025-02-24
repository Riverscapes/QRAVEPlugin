#!/bin/bash

# THIS IS JUST A CONVENIENCE SCRIPT FOR RUNNING:
#  
#              pip3 wheel rsxml==2.0.6 -w ./wheels --no-deps
# 

# This one is so we can develop and have code hinting. Use pip3 install -e /local/RiverscapesXML/python/packages/rsxml to debug locally
# Remove this and pip uninstall rsxml to use the wheel file
$QGIS_PATH/Contents/MacOS/bin/pip3 install rsxml==2.0.6
# This is the wheel file we want to package up
rm -fr ./wheels
$QGIS_PATH/Contents/MacOS/bin/pip3 wheel rsxml==2.0.6 -w ./wheels --no-deps
