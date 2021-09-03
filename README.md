# Riverscapes Analysis Visualization Explorer (QRAVE)

The Riverscapes Analysis Viewer and Explorer (RAVE) is a [QGIS](http://www.qgis.org/en/site/) plugin you can use to interact with riverscapes data. See the repository online documentation for more information:

<https://riverscapes.github.io/RiverscapesToolbar/>

## Acknowledgements

The Riverscapes Analysis Visualization Explorer Plugin software was developed by North Arrow Research Ltd., with funding form the [Bonneville Power Administration](https://www.bpa.gov/) (BPA) BPA Fish and Wildlife Program Project [#2011-006](http://www.cbfish.org/Project.mvc/Display/2011-006-00). Contributions were also made by [South Fork Research](http://www.southforkresearch.org/) and members of the [Fluvial Habitats Center](http://etal.joewheaton.org/a/joewheaton.org/et-al/) at Utah State University.

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


clone this repo to `qrave_toolbar_dev` so that `qrave_toolbar` is what gets used for deployment



## On OSX

before you start you need to set an environment variable to tell VSCode where QGIS's version of python is. This will depend on which shell you're using (The default is bash but we tend to use zsh)

1. You need to add the following line at the bottom of your `~/.bashrc` or `~/.zshrc` file:

```bash
export QGIS_PATH=/Applications/QGIS.app
```

***NOTE: This path must not end in a slash and must match what's on your system. If you're using the LTR version of QGIS this path might be something like `/Applications/QGIS-LTR.app`***

After this is done you need to restart VSCode completely (not just relloading the window).

2. You need this user setting to be on (it's in the user settings preferences)

```
"terminal.integrated.allowWorkspaceConfiguration": true
```

3. Open up the `Workspaces/OSXDev.code-workspace` using VSCode. This file contains all the right environment variables necessary to find and work with QGIS python libraries.


## Development resources

* [PyQGIS Developer Cookbook](https://docs.qgis.org/3.16/en/docs/pyqgis_developer_cookbook/index.html) - This should be the go-to for all your basic plugin development needs
* [QGIS API Documentation](https://qgis.org/api/) - Here you'll find Qgis-specific information for the API, endpoints, signals, slots etc.
* [Qt for Python](https://doc.qt.io/qtforpython-5/) - Qt is a C++ library so you need to specify the Python docs. This is where you find help with things like QtGui and QtWidgets



## License

Licensed under the [GNU General Public License Version 3](https://github.com/Riverscapes/RiverscapesToolbar/blob/master/LICENSE).

