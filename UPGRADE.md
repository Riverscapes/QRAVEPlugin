# QGIS 3 → QGIS 4 Upgrade Notes

This document records every change made to migrate the **Riverscapes Viewer (QRAVE) plugin**
from QGIS 3 / Qt 5 / PyQt5 to full compatibility with QGIS 4 / Qt 6 / PyQt6, while
retaining backward compatibility with QGIS 3.

---

## Background

QGIS 4 replaces the underlying Qt framework from **Qt 5 / PyQt5** to **Qt 6 / PyQt6**.
Three breaking changes affect almost every QGIS plugin:

| Change | Qt 5 (QGIS 3) | Qt 6 (QGIS 4) |
|---|---|---|
| Compiled resource registration | `QtCore.qRegisterResourceData()` | Function **removed** |
| Enum access style | Flat — `Qt.AlignCenter` | Scoped — `Qt.AlignmentFlag.AlignCenter` |
| Dialog / event-loop execution | `.exec_()` | `.exec()` (`exec_` removed) |

All imports already used `qgis.PyQt.*` (the QGIS compatibility shim), which is the
correct foundation for cross-version plugins — no bare `PyQt5` or `PyQt6` imports
were needed.

---

## New Files

### `src/compat.py`
Centralised Qt 5 / Qt 6 enum compatibility constants.  A single `try/except AttributeError`
block resolves every renamed enum at import time:

```python
# Qt 6 path tried first; falls back to Qt 5 flat names on AttributeError
try:
    ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter
    CHECKED      = Qt.CheckState.Checked
    LEFT_DOCK    = Qt.DockWidgetArea.LeftDockWidgetArea
    ...
except AttributeError:
    ALIGN_CENTER = Qt.AlignCenter
    CHECKED      = Qt.Checked
    LEFT_DOCK    = Qt.LeftDockWidgetArea
    ...
```

Also contains `QNetworkRequest` / `QNetworkReply` header/error-code constants that
changed namespaces between Qt 5 and Qt 6.

### `src/icon_utils.py`
Provides a single helper function `qrave_icon(alias: str) -> QIcon` that works in
both QGIS 3 and QGIS 4:

1. Tries `QIcon(":/plugins/qrave_toolbar/<alias>")` — the compiled Qt resource path
   (works in QGIS 3 where `qRegisterResourceData` succeeds).
2. If the icon is null (resources were not registered — QGIS 4), looks up the alias in
   an `_ALIAS_TO_FILE` mapping derived from `src/resources.qrc` and loads the file
   directly from the `Images/` directory on disk.

This is the only consumer-visible API change: every `QIcon(":/plugins/…")` call in
production code is replaced with `qrave_icon("…")`.

### `scripts/compile_resources.sh`
New cross-platform shell script that auto-detects `pyrcc6`/`pyrcc5` and
`pyuic6`/`pyuic5` and compiles resources and UI files for whichever Qt version is
present.

---

## Modified Files

### `src/resources.py` — critical fix for toolbar icons

**Root cause of the missing toolbar icons**: the file was compiled with
`PyQt5.pyrcc_main` and calls `QtCore.qRegisterResourceData()` at module load.
This function was removed in PyQt6; the call raised `AttributeError`, resources were
never registered, and every `QIcon(":/plugins/…")` returned a null (blank) icon.

**Fix**: wrapped both `qInitResources()` and `qCleanupResources()` in
`try/except AttributeError` so import never crashes, and the filesystem fallback in
`icon_utils.qrave_icon()` takes over automatically.

```python
# Before
def qInitResources():
    QtCore.qRegisterResourceData(rcc_version, qt_resource_struct, ...)

# After
def qInitResources():
    try:
        QtCore.qRegisterResourceData(rcc_version, qt_resource_struct, ...)
    except AttributeError:
        # Removed in PyQt6 — filesystem fallback via icon_utils.qrave_icon()
        pass
```

### `src/resources.qrc` — case-sensitivity bug fix

The alias `layers/MultiDot.png` referenced `../Images/layers/MultiDot16.png` but the
actual file on disk is `Multidot16.png` (lowercase **d**).  This was silently ignored
on case-insensitive macOS HFS+ but would cause resource compilation failures on
Linux.  Fixed to match the real filename.

### `src/qrave_toolbar.py`

| What changed | Detail |
|---|---|
| Icon loading | All `QIcon(":/plugins/qrave_toolbar/…")` → `qrave_icon("…")` |
| `Qt.ToolButtonTextBesideIcon` | → `TOOL_BTN_TEXT_BESIDE` from `compat` |
| `Qt.LeftDockWidgetArea` / `Qt.RightDockWidgetArea` | → `LEFT_DOCK` / `RIGHT_DOCK` from `compat` |
| `Qt.Vertical` | → `VERTICAL` from `compat` |
| `exec_()` (×6) | → `exec()` |

### `src/classes/context_menu.py`

The `MENUS` dict stores full `:/plugins/qrave_toolbar/X` paths.  Rather than
rewriting the dict, the `addAction` method now strips the prefix and calls
`qrave_icon(alias)`.  Also replaced the un-mapped `RaveAddIn_16px.png` (missing from
`.qrc` and disk) — the `icon_utils` alias map redirects it to `icon.svg`.

### `src/classes/remote_project.py`

- Rewrote `_get_icon()` to delegate to `qrave_icon()` with prefix stripping.
- Fixed `viewer-icon.png` → `viewer-icon.svg` (`.png` variant never existed in the
  compiled resources; the `.svg` is the correct alias).

### `src/classes/project.py`

- All `QIcon(":/plugins/qrave_toolbar/…")` → `qrave_icon("…")`.
- Fixed `viewer-icon.png` → `viewer-icon.svg` (line ~349).
- `Qt.gray` / `Qt.ForegroundRole` → `COLOR_GRAY` / `FOREGROUND_ROLE` from `compat`.

### `src/dock_widget.py`

- `QIcon(":/plugins/qrave_toolbar/refresh.png")` → `qrave_icon("refresh.png")`.
- `exec_()` (×2) → `exec()`.

### `src/file_selection_widget.py`

Replaced all flat enum accesses via `compat` imports:

| Old | New |
|---|---|
| `Qt.ItemIsUserCheckable` | `ITEM_FLAG_CHECKABLE` |
| `Qt.Checked` / `Qt.Unchecked` | `CHECKED` / `UNCHECKED` |
| `Qt.AlignRight \| Qt.AlignVCenter` | `ALIGN_RIGHT \| ALIGN_VCENTER` |

### `src/about_dialog.py`

- `Qt.RichText` (×4) → `RICH_TEXT`
- `Qt.Horizontal` → `HORIZONTAL`
- `QDialogButtonBox.Close` → `DIALOG_BTN_CLOSE`

### `src/meta_widget.py`

- `Qt.AlignCenter` (×3) → `ALIGN_CENTER`
- `Qt.blue` → `COLOR_BLUE`
- `Qt.ForegroundRole` → `FOREGROUND_ROLE`
- `exec_()` → `exec()`

### `src/options_dialog.py`

- `Qt.Horizontal` → `HORIZONTAL`

### `src/project_download_dialog.py`

- `Qt.AscendingOrder` → `ASCENDING_ORDER`

### `src/project_upload_dialog.py`

- `Qt.ItemIsEnabled` → `ITEM_FLAG_ENABLED`
- `Qt.AscendingOrder` → `ASCENDING_ORDER`
- `Qt.Checked` (×2) → `CHECKED`
- `exec_()` (×2) → `exec()`

### `src/ui/project_upload_dialog.py` *(auto-generated UI wrapper)*

- `QtCore.Qt.RichText` → `RICH_TEXT`
- `QtCore.Qt.ScrollBarAlwaysOff` → `SCROLL_BAR_ALWAYS_OFF`
- `QtCore.Qt.AlignCenter` (×4) → `ALIGN_CENTER`

### `src/ui/project_download_dialog.py` *(auto-generated UI wrapper)*

- `QtCore.Qt.RichText` → `RICH_TEXT`
- `QtCore.Qt.TextBrowserInteraction` → `TEXT_BROWSER_INTERACTION`

### `src/classes/data_exchange/uploader.py`

| Old | New |
|---|---|
| `QNetworkRequest.ContentLengthHeader` | `NET_CONTENT_LENGTH_HEADER` |
| `QNetworkReply.OperationCanceledError` (×5) | `NET_OP_CANCELED_ERROR` |
| `QNetworkReply.NoError` | `NET_NO_ERROR` |
| `loop.exec_()` (×2) | `loop.exec()` |

### `scripts/compile_pyrcc.bat`

- Updated to try `pyrcc6` / `PyQt6.pyrcc_main` before falling back to `pyrcc5`.
- Fixed long-standing typo: output file was `aboot.py` instead of `about.py`.

---

## How to Recompile Resources (optional)

The filesystem fallback in `icon_utils.py` means a recompile is **not required** for
the plugin to work in QGIS 4.  However, if you want the Qt resource system active in
QGIS 4 (e.g. for faster repeated icon lookups), recompile with Qt 6 tools:

```bash
# Cross-platform (auto-detects Qt version)
bash scripts/compile_resources.sh

# Manual — Qt 6
pyrcc6 src/resources.qrc -o src/resources.py

# Manual — Qt 5 (QGIS 3)
pyrcc5 src/resources.qrc -o src/resources.py
```

---

## Testing in QGIS

1. Install / update the plugin in your QGIS profile folder.
2. Open QGIS and use the **Plugin Reloader** plugin (`Ctrl+F5`) to hot-reload without
   restarting.
3. Confirm the Riverscapes Viewer toolbar appears with all icons visible.
4. Open a local project, a remote project, and the Data Exchange dialog to exercise
   the full icon set and the network upload/download paths.

---

## What Was NOT Changed

| Item | Reason |
|---|---|
| `test/qgis_interface.py` | Uses removed QGIS 2 APIs (`QgsMapLayerRegistry`, `QgsMapCanvasLayer`). The test harness pre-dates QGIS 3 and is not exercised by the plugin loader — left for a separate test-infrastructure overhaul. |
| `src/resources.py` binary data | The compiled byte arrays are Qt RCC v2 format, which is identical between Qt 5.8+ and Qt 6. No recompile is needed to get correct icon data. |
| `qgis.PyQt.*` import style | Already correct throughout — no bare `PyQt5`/`PyQt6` imports existed. |
