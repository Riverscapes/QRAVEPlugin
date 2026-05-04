@echo off
echo Compiling resources and UI files...

REM Try PyQt6 tools first (QGIS 4 / Qt6)
where pyrcc6 >nul 2>&1
if %errorlevel% == 0 (
    pyrcc6 src/resources.qrc -o src/resources.py
) else (
    python3 -m PyQt6.pyrcc_main src/resources.qrc -o src/resources.py
)

where pyuic6 >nul 2>&1
if %errorlevel% == 0 (
    pyuic6 src/ui/about_dialog.ui -o src/ui/about.py
) else (
    python3 -m PyQt6.uic.pyuic src/ui/about_dialog.ui -o src/ui/about.py
)

echo DONE
