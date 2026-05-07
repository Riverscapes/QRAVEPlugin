# Developer Guide — Riverscapes Viewer (QRAVEPlugin)

This document is the single source of truth for setting up a development environment,
building, linting, and deploying the plugin.  It covers **macOS**, **Windows**, and
**Ubuntu/Linux**, and both **QGIS 3** (Qt 5 / PyQt5) and **QGIS 4** (Qt 6 / PyQt6).

> **QGIS 3 → QGIS 4 migration notes** are in [`UPGRADE.md`](UPGRADE.md).

---

## Contents

1. [Prerequisites](#1-prerequisites)
2. [Clone the repo](#2-clone-the-repo)
3. [Platform setup](#3-platform-setup)
   - [macOS — QGIS 3](#31-macos--qgis-3)
   - [macOS — QGIS 4](#32-macos--qgis-4)
   - [Windows — QGIS 3](#33-windows--qgis-3)
   - [Ubuntu / Linux — QGIS 3](#34-ubuntu--linux--qgis-3)
4. [VS Code workspace files](#4-vs-code-workspace-files)
5. [Installing dev dependencies](#5-installing-dev-dependencies)
6. [Telemetry / secrets](#6-telemetry--secrets)
7. [Compiling resources and UI files](#7-compiling-resources-and-ui-files)
8. [Deploying to your local QGIS profile](#8-deploying-to-your-local-qgis-profile)
9. [Linting and formatting](#9-linting-and-formatting)
10. [Debugging in VS Code](#10-debugging-in-vs-code)
11. [Recommended QGIS plugins](#11-recommended-qgis-plugins)
12. [Code architecture notes](#12-code-architecture-notes)
13. [External resources](#13-external-resources)

---

## 1. Prerequisites

| Requirement | Version |
|---|---|
| QGIS | 3.22 or later (QGIS 4.x also supported) |
| Python | 3.9+ (bundled with QGIS) |
| VS Code | Any recent release |
| Git | Any recent release |

All Python tooling (PyQt, GDAL, etc.) is provided by the QGIS installation —
**do not** create a separate virtualenv for runtime code.  Dev tooling (`ruff`,
`debugpy`, `pb-tool`) is installed into QGIS's pip.

---

## 2. Clone the repo

The QGIS plugin loader looks for a directory named `riverscapes_viewer` in your plugins
folder.  Clone under a *different* name so you can keep the deploy target clean:

```bash
# macOS / Linux
git clone https://github.com/Riverscapes/QRAVEPlugin.git riverscapes_viewer_dev

# Windows (Git Bash or PowerShell)
git clone https://github.com/Riverscapes/QRAVEPlugin.git riverscapes_viewer_dev
```

> The deploy script (`scripts/deploy.py`) copies files into a correctly-named
> `riverscapes_viewer` folder inside your QGIS plugins directory automatically.

---

## 3. Platform setup

### 3.1 macOS — QGIS 3

#### a) Shell environment variables

Add the following to your `~/.zshrc` (or `~/.bashrc`):

```bash
export QGIS_PATH=/Applications/QGIS.app        # adjust if using LTR: /Applications/QGIS-LTR.app
export QGIS_PLUGINS="$HOME/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins"
```

> The path must **not** end in a slash.  Restart your shell (or `source ~/.zshrc`) after editing.

#### b) VS Code user setting

Open VS Code settings (`Cmd+,`) and ensure:

```json
"terminal.integrated.allowWorkspaceConfiguration": true
```

#### c) Open the correct workspace

```
Workspaces/QViewer-OSXDev.code-workspace
```

This workspace injects the QGIS 3 Python paths into every integrated terminal
automatically using the `$QGIS_PATH` variable.

#### d) Select the Python interpreter

1. Press `Cmd+Shift+P` → **Python: Select Interpreter** → **Enter interpreter path…**
2. Enter: `$QGIS_PATH/Contents/MacOS/bin/python3`
   (expand `$QGIS_PATH` manually, e.g. `/Applications/QGIS.app/Contents/MacOS/bin/python3`)

VS Code remembers this per-workspace.

#### e) Install dev dependencies

```bash
$QGIS_PATH/Contents/MacOS/bin/pip3 install -r requirements-dev.txt
```

#### f) Build the rsxml wheel

The `rsxml` package must be bundled as a local wheel (QGIS's network-isolated Python
cannot install it at runtime):

```bash
bash scripts/install_deps.sh
```

This installs `rsxml` into QGIS Python for local code-hinting and produces a
`wheels/rsxml-*.whl` file that gets bundled in the deploy package.

#### g) Qt Designer

```bash
$QGIS_PATH/Contents/MacOS/bin/designer
```

---

### 3.2 macOS — QGIS 4

QGIS 4 uses a different app bundle layout and Python 3.11+ / PyQt6.

#### a) Shell environment variables

```bash
export QGIS4_PATH=/Applications/QGIS4.app      # adjust to match the actual app name
export QGIS_PLUGINS="$HOME/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins"
```

> **Do not** set `PYTHONHOME` in your shell profile — it is injected only into the
> VS Code integrated terminal by the workspace file.  Setting it globally will break
> your system Python.

#### b) VS Code user setting

Same as QGIS 3:

```json
"terminal.integrated.allowWorkspaceConfiguration": true
```

#### c) Open the correct workspace

```
Workspaces/QViewer-OSXDev4.code-workspace
```

The yellow title bar distinguishes this window from the QGIS 3 workspace (green).

#### d) Select the Python interpreter

Do **not** point VS Code at the raw `python3.12` binary inside the app bundle — its
stdlib path is baked to the CI build server and crashes when run standalone.  Use the
wrapper script instead:

1. Press `Cmd+Shift+P` → **Python: Select Interpreter** → **Enter interpreter path…**
2. Enter: `/Applications/QGIS4.app/Contents/MacOS/python`
   (substitute your actual app name)

#### e) Install dev dependencies

```bash
$QGIS4_PATH/Contents/MacOS/bin/pip3 install -r requirements-dev.txt
```

#### f) Build the rsxml wheel

```bash
# Use the QGIS 4 pip
$QGIS4_PATH/Contents/MacOS/bin/pip3 install rsxml==2.2.1
rm -rf ./wheels
$QGIS4_PATH/Contents/MacOS/bin/pip3 wheel rsxml==2.2.1 -w ./wheels --no-deps
```

#### g) Qt Designer

```bash
$QGIS4_PATH/Contents/MacOS/bin/designer
```

---

### 3.3 Windows — QGIS 3

QGIS on Windows is distributed through the OSGeo4W installer, which provides its own
Python environment.

#### a) System environment variable

Add `OSGEO4W_ROOT` to your Windows user environment variables
(Start → Edit the system environment variables → Environment Variables):

```
OSGEO4W_ROOT=C:\OSGeo4W       # default path; adjust if you installed elsewhere
```

Set `QGIS_PLUGINS` to your plugin directory:

```
QGIS_PLUGINS=C:\Users\<YourName>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins
```

#### b) Launch VS Code from the OSGeo4W environment

Create a batch file (e.g. on your Desktop) to open VS Code with the full QGIS
environment loaded.  **Check all paths — they change between QGIS versions.**

```batch
@echo off
call "C:\OSGeo4W\bin\o4w_env.bat"
call %OSGEO4W_ROOT%\bin\qt5_env.bat
call %OSGEO4W_ROOT%\bin\py3_env.bat

path %PATH%;%OSGEO4W_ROOT%\apps\qgis\bin
path %PATH%;%OSGEO4W_ROOT%\apps\Qt5\bin
path %PATH%;%OSGEO4W_ROOT%\apps\Python39\Scripts

set QGIS_PREFIX_PATH=%OSGEO4W_ROOT:\=/%/apps/qgis
set GDAL_FILENAME_IS_UTF8=YES
set VSI_CACHE=TRUE
set VSI_CACHE_SIZE=1000000
set QT_PLUGIN_PATH=%OSGEO4W_ROOT%\apps\qgis\qtplugins;%OSGEO4W_ROOT%\apps\qt5\plugins

set PYTHONPATH=%PYTHONPATH%;%OSGEO4W_ROOT%\apps\qgis\python
set PYTHONPATH=%PYTHONPATH%;%OSGEO4W_ROOT%\apps\qgis\python\qgis

path %PATH%;%APPDATA%\Python\Python39\Scripts

pushd %~dp0
call "C:\Users\<YourName>\AppData\Local\Programs\Microsoft VS Code\bin\code.cmd"
```

> You need one of these batch files per QGIS version you develop against.

#### c) Open the correct workspace

Run the batch file above, then open:

```
Workspaces/QViewer-WindowsDev.code-workspace
```

#### d) Select the Python interpreter

1. Press `Ctrl+Shift+P` → **Python: Select Interpreter** → **Enter interpreter path…**
2. Enter: `%OSGEO4W_ROOT%\apps\Python39\python3.exe`
   (expand manually, e.g. `C:\OSGeo4W\apps\Python39\python3.exe`)

#### e) Install dev dependencies

In the VS Code terminal (launched from the batch file above):

```
pip install -r requirements-dev.txt
```

#### f) Compile resources

```batch
scripts\compile_pyrcc.bat
```

---

### 3.4 Ubuntu / Linux — QGIS 3

#### a) Install QGIS

Use the official QGIS repository for the most up-to-date packages:

```bash
# Add the QGIS signing key and repository (see https://qgis.org/en/site/forusers/alldownloads.html)
sudo apt install gnupg software-properties-common
sudo mkdir -p /etc/apt/keyrings
sudo wget -O /etc/apt/keyrings/qgis-archive-keyring.gpg https://download.qgis.org/downloads/qgis-archive-keyring.gpg

# Add the repo (adjust the distro codename as needed)
echo "deb [signed-by=/etc/apt/keyrings/qgis-archive-keyring.gpg] https://qgis.org/debian $(lsb_release -cs) main" \
  | sudo tee /etc/apt/sources.list.d/qgis.list

sudo apt update
sudo apt install qgis python3-qgis
```

#### b) Shell environment variables

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
export QGIS_PLUGINS="$HOME/.local/share/QGIS/QGIS3/profiles/default/python/plugins"
```

The QGIS Python binary and libraries live under `/usr/` on a standard apt install.
You do **not** need a `QGIS_PATH` variable on Linux.

#### c) Open the workspace

There is currently no dedicated Ubuntu workspace file.  Open the repo root folder
directly in VS Code (`File → Open Folder…`).

Point VS Code at the system QGIS Python interpreter:

1. Press `Ctrl+Shift+P` → **Python: Select Interpreter**
2. Select `/usr/bin/python3` (the version QGIS ships with)

Add these paths to your workspace or user `settings.json` for IntelliSense:

```json
"python.analysis.extraPaths": [
    "/usr/share/qgis/python",
    "/usr/share/qgis/python/plugins",
    "/usr/lib/python3/dist-packages"
]
```

#### d) Install dev dependencies

```bash
pip3 install --user -r requirements-dev.txt
```

Or install into the system Python if your pip supports it:

```bash
pip3 install -r requirements-dev.txt
```

#### e) Build the rsxml wheel

```bash
pip3 install rsxml==2.2.1
rm -rf ./wheels
pip3 wheel rsxml==2.2.1 -w ./wheels --no-deps
```

#### f) Qt Designer

```bash
designer   # or: qgis --designer
```

---

## 4. VS Code workspace files

| File | QGIS version | Title bar colour |
|---|---|---|
| `Workspaces/QViewer-OSXDev.code-workspace` | QGIS 3 (macOS) | Green |
| `Workspaces/QViewer-OSXDev4.code-workspace` | QGIS 4 (macOS) | Yellow |
| `Workspaces/QViewer-WindowsDev.code-workspace` | QGIS 3 (Windows) | Green |

Each workspace file:

- Sets `terminal.integrated.env.*` to inject the correct `PYTHONPATH` and `PATH`
  for that QGIS version so the integrated terminal is ready to run QGIS Python tools.
- Sets `python.analysis.extraPaths` so Pylance / IntelliSense can resolve `qgis.*`
  and `PyQt5`/`PyQt6` imports.
- Does **not** hard-code `python.defaultInterpreterPath` — use
  **Python: Select Interpreter** as described in each platform section above.

> **Important:** the workspace files use `${env:QGIS_PATH}` / `${env:QGIS4_PATH}` /
> `${env:OSGEO4W_ROOT}` variable expansion.  These environment variables must be set
> in your shell profile (macOS/Linux) or system environment (Windows) **before**
> opening the workspace.

---

## 5. Installing dev dependencies

`requirements-dev.txt` includes everything in `requirements.txt` plus:

| Package | Purpose |
|---|---|
| `ruff>=0.9` | Linter + formatter (replaces `pylint`, `autopep8`, `isort`) |
| `debugpy>=1.8` | Remote debugger — attach VS Code to running QGIS |
| `pb-tool>=3.1` | QGIS plugin build helper (`pb_tool compile`) |

Install using the QGIS-managed pip for your platform (see platform sections above).

Runtime-only dependencies (`lxml`, `requests`) are listed in `requirements.txt`.

> `rsxml` is **not** in either requirements file — it is installed via the wheel
> bundled in `wheels/`.  Build the wheel once with `scripts/install_deps.sh` (macOS)
> or the equivalent pip wheel command on other platforms.

---

## 6. Telemetry / secrets

Anonymous usage telemetry is sent on project open.  To enable telemetry in your local
dev build, copy the template and fill in the credentials:

```bash
cp secrets_TEMPLATE.json secrets.json
# Then edit secrets.json and fill in the real api-url and api-token values
```

`secrets.json` is listed in `.gitignore` and must **never** be committed.

---

## 7. Compiling resources and UI files

Qt resource files (`src/resources.qrc`) and Qt Designer UI files (`src/ui/*.ui`) must
be compiled to Python before the plugin will run.

### Automatic (recommended) — `compile_resources.sh`

A single script auto-detects whether Qt 5 or Qt 6 tools are available:

```bash
# macOS / Linux
bash scripts/compile_resources.sh

# Windows
scripts\compile_pyrcc.bat
```

The script tries tools in this order:
1. `pyrcc6` / `pyuic6` (standalone executables — Qt 6)
2. `python3 -m PyQt6.pyrcc_main` / `python3 -m PyQt6.uic.pyuic` (module fallback — Qt 6)
3. `pyrcc5` / `pyuic5` (standalone executables — Qt 5)
4. `python3 -m PyQt5.pyrcc_main` / `python3 -m PyQt5.pyuic` (module fallback — Qt 5)

### Using `pb_tool compile`

`pb_tool compile` also compiles resources and UI files using the QGIS-bundled tools:

```bash
# macOS QGIS 3
/Applications/QGIS.app/Contents/MacOS/bin/pb_tool compile

# macOS QGIS 4
/Applications/QGIS4.app/Contents/MacOS/bin/pb_tool compile

# Windows (from the OSGeo4W-launched terminal)
pb_tool compile
```

### Manual (single file)

```bash
# Qt 6
pyrcc6 src/resources.qrc -o src/resources.py
pyuic6 src/ui/about_dialog.ui -o src/ui/about.py

# Qt 5
pyrcc5 src/resources.qrc -o src/resources.py
pyuic5 -x src/ui/about_dialog.ui -o src/ui/about.py
```

> **Note:** A recompile is not strictly required for the plugin to function in
> QGIS 4 — the `icon_utils.qrave_icon()` fallback loads icons directly from the
> `Images/` directory on disk when the Qt resource system is unavailable.

---

## 8. Deploying to your local QGIS profile

`scripts/deploy.py` copies the plugin into your QGIS plugins directory and creates a
distributable zip:

```bash
# Make sure QGIS_PLUGINS is set (see platform sections above)
python scripts/deploy.py
```

The script will:
1. Ask you to confirm the current version (from `__version__.py`).
2. Ask you to confirm it is safe to delete the existing deploy folder.
3. Copy only the files listed in `keep_patterns` (Python source, resources, wheels, `secrets.json`, etc.).
4. Write a clean `metadata.txt` (strips the `DEV_COPY` marker, substitutes the real version).
5. Create a `riverscapes_viewer-<version>.zip` alongside the deploy folder.

> **`secrets.json` must exist before running the deploy** — without it, telemetry will
> be silently disabled in the deployed plugin.  Copy `secrets_TEMPLATE.json` to
> `secrets.json` and fill in the credentials before deploying (see [§6](#6-telemetry--secrets)).

The `QGIS_PLUGINS` environment variable must point to your plugins directory.  The
deploy directory must be different from the source directory.

---

## 9. Linting and formatting

This repo uses **[Ruff](https://docs.astral.sh/ruff/)** as the single tool for
linting, formatting, and import sorting.  It replaces the old `pylint` + `autopep8` +
`isort` stack entirely.

All rules are configured in `pyproject.toml`.

| Command | What it does |
|---|---|
| `ruff check .` | Lint only |
| `ruff format .` | Format only (replaces autopep8) |
| `ruff check --fix .` | Lint + auto-fix safe issues |
| `ruff check --fix --unsafe-fixes .` | Lint + fix everything possible |

### VS Code integration

The Ruff VS Code extension (`charliermarsh.ruff`) is in the recommended extensions list
(`.vscode/extensions.json`).  With it installed, on every file save VS Code will
automatically:

1. **Format** — equivalent to `ruff format`
2. **Fix safe lint issues** — equivalent to `ruff check --fix`
3. **Sort imports** — equivalent to `isort` via Ruff's built-in `I` rule set

### Key configuration choices

- **Line length:** 240 (matches the legacy codebase; enforced by `editor.rulers` in
  `.vscode/settings.json` and `max_line_length` in `.editorconfig`)
- **Target Python version:** 3.9 (oldest Python bundled with QGIS 3.x)
- **Auto-generated files** (`src/ui/*.py`): naming and style rules suppressed
- **Qt / QGIS naming:** `N802`, `N803`, `N806`, `N815`, `N816` suppressed to allow
  camelCase as required by PyQt slot signatures and QGIS API overrides

---

## 10. Debugging in VS Code

1. Install the **debugvs** plugin in QGIS (see [§11](#11-recommended-qgis-plugins)).
2. Set `RS_DEBUG=true` in QGIS → Settings → Options → Environment.
3. Start QGIS.
4. Click the **Visual Studio Code** button in the Plugins toolbar inside QGIS.
5. In VS Code, run the **QGIS Debug** launch configuration
   (`Run → Start Debugging` or `F5`).
6. Drop a breakpoint and trigger the code path in QGIS.

`debugpy` (the modern replacement for `ptvsd`) is listed in `requirements-dev.txt`
and provides the attach-to-process functionality.

---

## 11. Recommended QGIS plugins

Install these from QGIS → Plugins → Manage and Install Plugins:

| Plugin | Purpose |
|---|---|
| [Plugin Reloader](https://github.com/borysiasty/plugin_reloader) | Hot-reload the plugin without restarting QGIS (`Ctrl+F5`) |
| [First Aid](https://github.com/wonder-sk/qgis-first-aid-plugin) | Better Python error traces and a built-in debugger |
| [debugvs](https://github.com/lmotta/debug_vs_plugin/wiki) | Exposes the VS Code attach button in the QGIS toolbar |
| [Plugin Builder 3](http://g-sherman.github.io/Qgis-Plugin-Builder) | Scaffold new QGIS plugins (optional) |

---

## 12. Code architecture notes

### Python 3.9 type annotation compatibility

QGIS 3 ships Python 3.9.  The `X | None` union syntax and built-in generic
aliases (`list[str]`, `dict[str, str]`) crash at **runtime** on Python 3.9 when
used in annotations unless the file starts with:

```python
from __future__ import annotations
```

This import (PEP 563, available since Python 3.7) makes all annotations lazily
evaluated strings, so the modern syntax is never executed by the interpreter.
**Every file that uses `X | Y`, `X | None`, or built-in generics in annotations
must have this as its first non-docstring import.**  It is safe alongside
`pyqtSignal` because signal declarations use `pyqtSignal(Type, ...)` argument
syntax, not annotation syntax.

### `src/compat.py` — Qt 5 / Qt 6 enum shims

Qt 6 / PyQt6 uses **scoped** enums (`Qt.AlignmentFlag.AlignCenter`) while Qt 5 / PyQt5
used **flat** enums (`Qt.AlignCenter`).  Rather than sprinkling `try/except` blocks
throughout the codebase, all shared enum constants live in `src/compat.py`:

```python
from src.compat import ALIGN_CENTER, CHECKED, LEFT_DOCK   # etc.
```

**Never** access `Qt.*` enum values directly in production code — always import from
`compat`.  Add new constants to `compat.py` whenever you use a Qt enum that isn't
already there.

### `src/icon_utils.py` — cross-version icon loading

In QGIS 3 / PyQt5, compiled resource files register icons via
`QtCore.qRegisterResourceData()`, so `QIcon(":/plugins/qrave_toolbar/…")` works.
In QGIS 4 / PyQt6, that function was removed.

`icon_utils.qrave_icon(alias)` handles both cases:

1. Tries the compiled resource path (`:/plugins/qrave_toolbar/<alias>`).
2. If the resulting icon is null (resources not registered), looks up the alias in
   the `_ALIAS_TO_FILE` map and loads the file directly from `Images/` on disk.

**Always use `qrave_icon("…")` instead of `QIcon(":/plugins/…")` in all production code.**

### QGIS 4 backward-compatible layer tree API

The following layer-tree methods were removed or changed in QGIS 4:

| Do not use | Use instead |
|---|---|
| `group.insertGroup(idx, name)` | `group.addGroup(name)` |
| `group.insertLayer(idx, layer)` | `group.insertChildNode(-1, QgsLayerTreeLayer(layer))` |
| `child.nodeType() == 0` | `isinstance(child, QgsLayerTreeGroup)` |
| `if not parentGroup:` | `if parentGroup is None:` (PyQt6 maps `__len__` to child count) |

See [`UPGRADE.md`](UPGRADE.md) for the full rationale.

---

## 13. External resources

- [PyQGIS Developer Cookbook](https://docs.qgis.org/3.16/en/docs/pyqgis_developer_cookbook/index.html)
- [QGIS API Documentation](https://qgis.org/api/)
- [Qt for Python (PyQt5)](https://doc.qt.io/qtforpython-5/)
- [Qt for Python (PyQt6)](https://doc.qt.io/qtforpython-6/)
- [Ruff documentation](https://docs.astral.sh/ruff/)
- [pb_tool documentation](http://g-sherman.github.io/plugin_build_tool/)
