# Riverscapes Viewer

The Riverscapes Viewer (formerly QRAVE) is a [QGIS](http://www.qgis.org/en/site/) plugin you can use to interact with riverscapes data. See the online documentation for more information:

[viewer.riverscapes.net](https://viewer.riverscapes.net/software-help/help-qgis/)

## Acknowledgements

The Riverscapes Viewer Plugin software was developed by North Arrow Research Ltd., with funding form the [Bonneville Power Administration](https://www.bpa.gov/) (BPA) BPA Fish and Wildlife Program Project [#2011-006](http://www.cbfish.org/Project.mvc/Display/2011-006-00). Contributions were also made by [South Fork Research](http://www.southforkresearch.org/) and members of the [Fluvial Habitats Center](http://etal.joewheaton.org/a/joewheaton.org/et-al/) at Utah State University.

## Developing on Windows OR OSX

Make sure the `RS_DEBUG=true` is set in QGIS Environment

## Developing on windows

1. Make a batch file on your desktop to launch VSCode with the QGIS development paths and environment

fill in paths where appropriate.  NOTE: ALL THESE PATHS SHOULD BE CHECKED. They change from version to version!! You'll need one of these files for each version of QGIS that you are developing on. You only need this file if you want to debug using breakpoints.

```batch
@echo off
@REM First one needs an explicit path
call "C:\Program Files\QGIS 3.16.10\bin\o4w_env.bat"
call %OSGEO4W_ROOT%\bin\qt5_env.bat
call %OSGEO4W_ROOT%\bin\py3_env.bat

@echo off
path %PATH%;%OSGEO4W_ROOT%\apps\qgis-ltr\bin
path %PATH%;%OSGEO4W_ROOT%\apps\Qt5\bin
path %PATH%;%OSGEO4W_ROOT%\apps\Python39\Scripts

rem o4w_env.bat starts with a clean path, so add what you need

set QGIS_PREFIX_PATH=%OSGEO4W_ROOT%:\=/%/apps/qgis-ltr
set GDAL_FILENAME_IS_UTF8=YES
rem Set VSI cache to be used as buffer, see #6448
set VSI_CACHE=TRUE
set VSI_CACHE_SIZE=1000000
set QT_PLUGIN_PATH=%OSGEO4W_ROOT%\apps\qgis-ltr\qtplugins;%OSGEO4W_ROOT%\apps\qt5\plugins

set PYTHONPATH=%PYTHONPATH%;%OSGEO4W_ROOT%\apps\qgis-ltr\python\
set PYTHONPATH=%PYTHONPATH%;%OSGEO4W_ROOT%\apps\qgis-ltr\python\qgis

@REM We include local python scripts since this is where pip installs to for ptvsd and pb_tool
path %PATH%;%APPDATA%\Python\Python39\Scripts

pushd %~dp0
call "C:\Users\Matt\AppData\Local\Programs\Microsoft VS Code\bin\code.cmd"
```

When you run this batch file you'll get a vscode window. Use this window to open `Workspaces\WindowsDev.code-workspace`.

Go to the terminal and install pb-tool and other python development dependencies if you haven't already:

```
pip install pylint autopep8 ptvsd pb-tool
```


2. Download the following plugins in QGIS:

* [Plugin Reloader](https://github.com/borysiasty/plugin_reloader) -- Handy tool to reload all the code for a given plugin so you don't need to close QGIS.
* [First Aid](https://github.com/wonder-sk/qgis-first-aid-plugin) -- Provides Python debugger and replaces the default Python error handling in QGIS. This one is optional but highly recommended. It gives error traces you might not get otherwise and makes QGIS a lot less black-box.
* [debugvs](https://github.com/lmotta/debug_vs_plugin/wiki) -- This plugin is for debugging in Visual Studio ( tested in Visual Studio Code). For use, run this plugin and enable the Debug (Python:Attach) in Visual Studio. Need install the ptvsd's module(pip3 install ptvsd).
* [Plugin Builder 3](http://g-sherman.github.io/Qgis-Plugin-Builder) -- Creates a QGIS plugin template for use as a starting point in plugin development. Not totally necessary but good to have if you want to build plugins.


clone this repo to `riverscapes_viewer_dev` so that `riverscapes_viewer` is what gets used for deployment



## On OSX

before you start you need to set two environment variables to tell VSCode where QGIS's version of python is. This will depend on which shell you're using (The default is bash but we tend to use zsh)

1. You need to add the following line at the bottom of your `~/.bashrc` or `~/.zshrc` file:

```bash
export QGIS_PATH=/Applications/QGIS.app
export QGIS_PLUGINS=/Users/USERNAME/Library/Application Support/QGIS/QGIS3/profiles/user/python/plugins
```

***NOTE: This path must not end in a slash and must match what's on your system. If you're using the LTR version of QGIS this path might be something like `/Applications/QGIS-LTR.app`***

After this is done you need to restart VSCode completely (not just relloading the window).

2. You need this user setting to be on (it's in the user settings preferences)

```
"terminal.integrated.allowWorkspaceConfiguration": true
```

3. Open up the `Workspaces/OSXDev.code-workspace` using VSCode. This file contains all the right environment variables necessary to find and work with QGIS python libraries.

Launching the Qt designer:

```bash
$QGIS_PATH/Contents/MacOS/bin/designer 
```

## `rsxml` dependency

This plugin uses the `rsxml` library to parse and manipulate Riverscapes XML files. This library is available on PyPi butso you need to install it manually as a wheel so that the plugin can use it. You can install it using the following command:

```bash
sh ./scripts/install_deps.sh
```

THis is just running the following command:

```bash
$QGIS_PATH_PYTHON_PATH/pip3 wheel rsxml==2.2.1 -w ./wheels --no-deps
```

## Development resources

* [PyQGIS Developer Cookbook](https://docs.qgis.org/3.16/en/docs/pyqgis_developer_cookbook/index.html) - This should be the go-to for all your basic plugin development needs
* [QGIS API Documentation](https://qgis.org/api/) - Here you'll find Qgis-specific information for the API, endpoints, signals, slots etc.
* [Qt for Python](https://doc.qt.io/qtforpython-5/) - Qt is a C++ library so you need to specify the Python docs. This is where you find help with things like QtGui and QtWidgets


## Buildsing the UI files

```
pyuic5 -x input.ui -o output.py
```

## License

Licensed under the [GNU General Public License Version 3](https://github.com/Riverscapes/RiverscapesToolbar/blob/master/LICENSE).

## QT Designer

### Installing `pb_tool`

First make sure that pb_tool is installed (note that you may need to adjust your QGIS paths in the commands below )

```
/Applications/QGIS-LTR.app/Contents/MacOS/bin/pip3 install pb_tool
```

### Running `pb_tool` compile

You just need to run `pb_tool compile` from the installed QGIS python environment. Make sure you're in the repo root for QRavePlugin when you do that

pb_tool compile will do 2 things:

1. It will run pyrcc5 on the `src/resources.qrc` file and compile it to a python file in the `src` directory
2. It will run pyuic5 on the `src/ui/*.ui` files and compile them to python files in the `src/ui` directory

```bash
> /Applications/QGIS-LTR.app/Contents/MacOS/bin/pb_tool compile     
Skipping ./src/ui/dock_widget.ui (unchanged)
Skipping ./src/ui/meta_widget.ui (unchanged)
Skipping ./src/ui/meta_widget.ui (unchanged)
Skipping ./src/ui/about_dialog.ui (unchanged)
Skipping ./src/ui/options_dialog.ui (unchanged)
Compiling ./src/ui/project_upload_dialog.ui to ./src/ui/project_upload_dialog.py
Compiled 1 UI files
Compiling ./src/resources.qrc to ./src/resources.py
Compiled 1 resource files
```


On MacOS

`/Applications/QGIS.app/Contents/MacOS/bin/designer`

## Debugging

1. Make sure the Plugin Reloader plugin is installed in QGIS.
1. Start QGIS
1. Click the Visual Studio Code button on the Plugins toolbar.
1. Click the play button in Visual Studio Code for the "QGIS Debug" process. This will fail if the previous step was not performed.
1. Drop a breakpoint.
1. Cause the breakpoint to fire. VSCode should pause at the breakpoint.

```
https://github.com/planetfederal/qgis-connect-plugin/blob/885773aa0bed618f85bd15d4c67ccbbcf9bee64c/boundlessconnect/gui/connectdockwidget.py#L430
```



