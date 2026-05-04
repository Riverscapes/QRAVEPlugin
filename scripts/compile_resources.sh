#!/usr/bin/env bash
# Compile Qt resources and UI files for QGIS 3 (Qt5) and QGIS 4 (Qt6).
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PLUGIN_DIR"

# Resources
if command -v pyrcc6 &>/dev/null; then
    echo "Using pyrcc6..."
    pyrcc6 src/resources.qrc -o src/resources.py
elif python3 -c "import PyQt6" &>/dev/null; then
    echo "Using PyQt6.pyrcc_main..."
    python3 -m PyQt6.pyrcc_main src/resources.qrc -o src/resources.py
elif command -v pyrcc5 &>/dev/null; then
    echo "Using pyrcc5..."
    pyrcc5 src/resources.qrc -o src/resources.py
else
    echo "Using PyQt5.pyrcc_main..."
    python3 -m PyQt5.pyrcc_main src/resources.qrc -o src/resources.py
fi

# UI files
if command -v pyuic6 &>/dev/null; then
    echo "Using pyuic6..."
    pyuic6 src/ui/about_dialog.ui -o src/ui/about.py
elif python3 -c "import PyQt6" &>/dev/null; then
    python3 -m PyQt6.uic.pyuic src/ui/about_dialog.ui -o src/ui/about.py
elif command -v pyuic5 &>/dev/null; then
    pyuic5 src/ui/about_dialog.ui -o src/ui/about.py
else
    python3 -m PyQt5.pyuic src/ui/about_dialog.ui -o src/ui/about.py
fi

echo "DONE"
