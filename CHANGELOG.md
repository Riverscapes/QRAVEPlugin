## 1.0.1 ***(February 24, 2025)***

### Fixed
- Fixing QGIS crash issue. #141


## 1.0.0 ***(October 11, 2024)***

### Changed
- Remove Experimental Tag


## 0.9.5 ***(October 11, 2024)***

### Fixed
- Project uploader using wrong organization ownership #132


## 0.9.4 ***(September 9, 2024)***

### Added
- License agreement for the plugin

### Changed
- RSXML Module updated to version 2.0.6
- Warehouse renamed to Data Exchange #129

## 0.9.3 ***(June 19, 2024)***

### Added
- Include QRiS metric definitions in the resources sync.


## 0.9.2 ***(April 26, 2024)***

### Added
- Project Data Exchange Uploader

### Fixed
- Close All Projects Throws Error #107
- Better Business logic handling
- Message bar was not showing up #123
- GraphQL files not being included in the deploy #117

### Changed
- Removed additional "QRAVE" references

## 0.9.1 ***(March 27, 2024)***

### Fixed
- Bug with "Show Basemaps in Project Tree" checkbox throwing error
- Bug when adding Basemaps to versions of QGIS < 3.28
- View in Warehouse button menu item now working properly with new Riverscapes Projects version

### Changed
- removed lingering references to QRAVE
- Updated urls to riverscapes.net
- Update Settings window title

## 0.9.0 ***(December 15, 2023)***

* Refresh QRAVE as Riverscapes Viewer
* logo and icon changes

## 0.8.1 ***(March 24, 2023)***

* Add framework for QRiS integration
* Support for relative paths in project XML

## 0.5.1 ***(June 1, 2021)***

* Hotfix patch to allow for some new Riverscapes functionality

## 0.5.0 ***(June 1, 2021)***

### New Features

* [Update to support more basemap Types (XYZ and TMS)](https://github.com/Riverscapes/QRAVEPlugin/issues/21)
* [Adding the ability to opt-out of automatic updates](https://github.com/Riverscapes/QRAVEPlugin/issues/23)

### Bug Fixes

* [Failing gracefully when the project XML doesn't conform to the latest version](https://github.com/Riverscapes/QRAVEPlugin/issues/28)
* [Empty tree branches don't cause crashes anymore](https://github.com/Riverscapes/QRAVEPlugin/issues/15)
* [Raster transparencies now work correctly](https://github.com/Riverscapes/QRAVEPlugin/issues/22)
* [...lots of little annoying bugs](https://github.com/Riverscapes/QRAVEPlugin/issues/18)


## 0.4.0 ***(May 13, 2021)***

* [Fixed a blocking bug that prevented working on QGIS Versions less than 3.18](https://github.com/Riverscapes/QRAVEPlugin/issues/16)
* [Fixed an issue where layers with the same name in different projects cannot be added to the map](https://github.com/Riverscapes/QRAVEPlugin/issues/14)
* [Fixed: Project-level "Add all to map" broken #13](https://github.com/Riverscapes/QRAVEPlugin/issues/13)
* [Regression: Transparency issue fixed and Vectors now supported](https://github.com/Riverscapes/QRAVEPlugin/issues/2)
* Misc problems and code cleanups.

## 0.3.0 ***(May 10, 2021)***

* [Fixed the about screen regression issue](https://github.com/Riverscapes/QRAVEPlugin/issues/11)
* Optimization of unnecessarily large graphics to reduce overall plugin size. (7Mb --> 542Kb)
* Fixed several small OSX-only bugs and provided a development environment that is usable on that OS.


## 0.2.0 ***(May 4, 2021)***

### Bug Fixes

* [Respect the "collapsed" attribute in the business logic](https://github.com/Riverscapes/QRAVEPlugin/issues/8)
* [Metadata.txt version not updating on plugin build.](https://github.com/Riverscapes/QRAVEPlugin/issues/7)
* [Acknowledgements Not Updating](https://github.com/Riverscapes/QRAVEPlugin/issues/6)
* [Toolbar Icons Disabled upon first install](https://github.com/Riverscapes/QRAVEPlugin/issues/5)
* [Symbology qml not loading correctly](https://github.com/Riverscapes/QRAVEPlugin/issues/4)
* [Multiple projects open at once](https://github.com/Riverscapes/QRAVEPlugin/issues/3)
* [Support transparency attribute](https://github.com/Riverscapes/QRAVEPlugin/issues/2)


## 0.0.1

First version. Everything is new.