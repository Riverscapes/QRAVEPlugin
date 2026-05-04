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

## Hotfix — Layer hierarchy still broken: all groups and layers added at root level

**Reported after the layer-tree API fix above.**

Three compounding bugs were identified and fixed, all in `src/classes/qrave_map_layer.py`.

### Bug 1 (Critical) — PyQt6 ownership transfer invalidates group reference

The QGIS 4 fallback introduced in the previous fix used:

```python
thisGroup = QgsLayerTreeGroup(sGroupName)       # Python allocates; Python owns
parentGroup.insertChildNode(sGroupOrder, thisGroup)  # C++ takes ownership
return thisGroup                                 # ← wrapper now INVALID in PyQt6
```

In PyQt6/sip6, when `insertChildNode` transfers ownership to C++, the original Python wrapper is marked as transferred and becomes falsy. The `_prepare_parent_group` loop then hits `if not parentGroup:` on the very next iteration and resets to `layerTreeRoot()`. Every group in the ancestry chain is therefore created at root level (not nested), and the layer lands at root too.

**Fix**: replaced `QgsLayerTreeGroup() + insertChildNode` with `addGroup()`, which is a C++ method that allocates and inserts the node internally and returns a stable, C++-managed Python reference — no ownership transfer, no invalidation.

### Bug 2 (High) — `findGroup()` searches recursively, matching wrong project's groups

`QgsLayerTreeGroup.findGroup(name)` recurses through the entire subtree. With multiple Riverscapes projects open, it could return a same-named group from a different project, causing layers to be inserted under the wrong project.

**Fix**: replaced `findGroup` in `_addgrouptomap` with a direct-children loop using `isinstance(child, QgsLayerTreeGroup)` — only direct children of `parentGroup` are checked.

### Bug 3 (Medium) — `item.row()` is a plugin-model index, not a QGIS tree index

`item.row()` returns the row of the `QStandardItem` inside the plugin's own dock-widget model. Passing this as the insertion index into a `QgsLayerTreeGroup` (which may have a completely different child count and ordering) produces undefined behaviour — QGIS 3 silently clamped it; QGIS 4 may not.

**Fix**: replaced all four `insertChildNode(item.row(), QgsLayerTreeLayer(rOutput))` calls with `insertChildNode(-1, QgsLayerTreeLayer(rOutput))`. Passing `-1` as the index causes QGIS to append at the end of the group regardless of current child count — equivalent to append semantics, but using `insertChildNode` which exists in both QGIS 3 and QGIS 4.

(`appendChildNode` was the first attempted fix here but was itself QGIS-4-only and does not exist on `QgsLayerTree` / `QgsLayerTreeGroup` in QGIS 3, producing `'QgsLayerTree' object has no attribute 'appendChildNode'`.)

---

## Hotfix — `IndexError: list index out of range` + groups still flat at root (QGIS 4.0.1)

**Reported with full stack trace from QGIS 4.0.1-Norrköping.**

Two bugs identified from the trace.

### Bug A — `if not parentGroup` is falsy for an empty `QgsLayerTreeGroup` in PyQt6

In PyQt6/sip6, `QgsLayerTreeGroup` exposes `__len__` mapped to its child count.
A freshly-created empty group has 0 children → `bool(group) == False` → `not group` is `True`.

The `_prepare_parent_group` loop and `_addgrouptomap` both used `if not parentGroup:` as a
"not yet initialised" guard. In PyQt6 this guard fired on every freshly-created group,
resetting `parentGroup` to `layerTreeRoot()` at the start of every loop iteration. Every
group in the ancestry chain was therefore created at root level (not nested), and the layer
landed at root too.

**Fix**: replaced every `if not parentGroup:` with `if parentGroup is None:` (3 sites across
`_addgrouptomap` and `_prepare_parent_group`).

| File | Line | Before | After |
|---|---|---|---|
| `qrave_map_layer.py` | ~153 | `if not parentGroup:` | `if parentGroup is None:` |
| `qrave_map_layer.py` | ~248 | `if not parentGroup:` (in loop) | `if parentGroup is None:` |
| `qrave_map_layer.py` | ~258 | `if not parentGroup:` (post-loop) | `if parentGroup is None:` |

### Bug B — `IndexError` when a layer exists in the registry but not in the layer tree

`get_layer_ancestry` returns `[]` when a layer is registered with the project but absent
from the layer tree (e.g. left over from earlier broken insertions). The existence-check
loop then hit `lyr[0]` on an empty list:

```python
# Before — crashes with IndexError when lyr == []
elif lyr[0] == ancestry[0][0]:

# After — short-circuit guard
elif lyr and lyr[0] == ancestry[0][0]:
```

---

## Hotfix — Layer hierarchy not created in QGIS 4

**Reported after initial migration.**

Only one file required changes: `src/classes/qrave_map_layer.py`.

### Root causes

QGIS 4 removed or altered three layer-tree convenience methods and an enum comparison:

| # | Line(s) | Old API | New API | Impact |
|---|---|---|---|---|
| 1 | 7–10 | *(missing imports)* | Added `QgsLayerTreeGroup`, `QgsLayerTreeLayer` to `qgis.core` imports | Required by fixes below |
| 2 | ~161 | `parentGroup.insertGroup(idx, name)` | `hasattr` guard: QGIS 3 keeps `insertGroup`; QGIS 4 falls back to `QgsLayerTreeGroup(name)` + `insertChildNode(idx, node)` | Groups not positioned correctly / AttributeError |
| 3 | ~349 | `parentGroup.insertLayer(idx, layer)` | `parentGroup.insertChildNode(idx, QgsLayerTreeLayer(layer))` | Layers dumped at tree root instead of inside groups |
| 4 | ~437 | same `insertLayer` | same `insertChildNode` fix | Same as above (remote vector tiles) |
| 5 | ~629, ~683 | same `insertLayer` (×2) | same `insertChildNode` fix | Same as above (remote raster tiles, incl. retry path) |
| 6 | ~707 | `child.nodeType() == 0` | `isinstance(child, QgsLayerTreeGroup)` | `remove_project_from_map` silently did nothing in QGIS 4 because PyQt6 scoped-enum `!=` integer `0` |

`insertChildNode(index, QgsLayerTreeLayer(layer))` is the low-level base API that has been
stable across all QGIS 3.x and QGIS 4.x releases; the `insertLayer` / `insertGroup`
convenience wrappers were thin QGIS 3 additions that were removed in QGIS 4.

---

## Hotfix — `ContextMenu object has no attribute exec_`

**Reported after initial migration.**

One `exec_()` call was missed during the bulk `exec_` → `exec` pass:

| File | Line | Before | After |
|---|---|---|---|
| `src/dock_widget.py` | 1101 | `menu.exec_(…)` | `menu.exec(…)` |

`menu` is a `ContextMenu` instance (subclass of `QMenu`).  In PyQt6, `QMenu.exec_()` no longer exists — only `exec()` — so every right-click on the project tree raised:

```
AttributeError: ContextMenu object has no attribute exec_
```

Verification: `grep -rn "exec_(" src/` now returns **zero results**.

---

## What Was NOT Changed

| Item | Reason |
|---|---|
| `test/qgis_interface.py` | Uses removed QGIS 2 APIs (`QgsMapLayerRegistry`, `QgsMapCanvasLayer`). The test harness pre-dates QGIS 3 and is not exercised by the plugin loader — left for a separate test-infrastructure overhaul. |
| `src/resources.py` binary data | The compiled byte arrays are Qt RCC v2 format, which is identical between Qt 5.8+ and Qt 6. No recompile is needed to get correct icon data. |
| `qgis.PyQt.*` import style | Already correct throughout — no bare `PyQt5`/`PyQt6` imports existed. |
