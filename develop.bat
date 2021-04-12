@echo off
call "%QGIS_ROOT%\bin\o4w_env.bat"
call "%QGIS_ROOT%\bin\py3_env.bat"
call "%QGIS_ROOT%\bin\qt5_env.bat"

set VSI_CACHE=TRUE
set VSI_CACHE_SIZE=1000000

pushd %~dp0
call "%VSCODE_ROOT%\code.cmd" .\Workspaces\QRAVEWindowsDev.code-workspace
