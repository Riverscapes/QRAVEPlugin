"""Unit tests for src/classes/rspaths.py

These tests have no QGIS dependency — rspaths.py is pure stdlib (os only).
They verify cross-platform path handling for three functions:

  parse_rel_path   - normalise separators and redundant components
  safe_make_relpath - convert an absolute path to relative (pass-through if already relative)
  safe_make_abspath - convert a relative path to absolute (pass-through if already absolute)
"""

import os
import sys
import unittest

# Add src/classes directly so we can import rspaths without triggering
# src/__init__.py, which has a hard dependency on qgis.core.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "classes")))

from rspaths import parse_rel_path, safe_make_abspath, safe_make_relpath

# A stable absolute directory used as the reference cwd throughout.
CWD = "/projects/myproject"


# ── parse_rel_path ────────────────────────────────────────────────────────────


class TestParseRelPath(unittest.TestCase):
    """parse_rel_path(path) → os.path.normpath(path.replace('\\', '/'))"""

    # ── separator handling ───────────────────────────────────────────────────

    def test_unix_path_returned_unchanged(self):
        """A plain Unix-style path that is already clean is returned unchanged."""
        self.assertEqual(parse_rel_path("foo/bar/baz.shp"), "foo/bar/baz.shp")

    def test_windows_backslashes_converted(self):
        """Windows-style backslashes are replaced and then normalised."""
        self.assertEqual(parse_rel_path("layers\\dem\\slope.tif"), os.path.join("layers", "dem", "slope.tif"))

    def test_mixed_separators_normalised(self):
        """A path with both backslashes and forward slashes is normalised."""
        self.assertEqual(parse_rel_path("layers\\dem/slope.tif"), os.path.join("layers", "dem", "slope.tif"))

    def test_all_backslashes_deep_path(self):
        """A deeply nested all-backslash path is fully converted."""
        self.assertEqual(parse_rel_path("a\\b\\c\\d\\file.gpkg"), os.path.join("a", "b", "c", "d", "file.gpkg"))

    def test_windows_drive_letter_path(self):
        """A Windows-style C:\\... path has its backslashes converted (POSIX passthrough)."""
        result = parse_rel_path("C:\\Users\\project\\dem.tif")
        # After replace: C:/Users/project/dem.tif; normpath keeps it on POSIX
        self.assertEqual(result, os.path.normpath("C:/Users/project/dem.tif"))

    def test_windows_root_backslash(self):
        """A bare Windows backslash root converts to '/'."""
        self.assertEqual(parse_rel_path("\\"), "/")

    # ── redundant separator removal ──────────────────────────────────────────

    def test_double_slashes_collapsed(self):
        """Consecutive forward slashes are collapsed to a single separator."""
        self.assertEqual(parse_rel_path("foo//bar///baz.shp"), os.path.join("foo", "bar", "baz.shp"))

    def test_trailing_slash_removed(self):
        """A trailing slash is stripped by normpath."""
        self.assertEqual(parse_rel_path("foo/bar/"), os.path.join("foo", "bar"))

    # ── dot and double-dot resolution ────────────────────────────────────────

    def test_single_dot_component_removed(self):
        """A './' in the middle of a path is collapsed."""
        self.assertEqual(parse_rel_path("foo/./bar.shp"), os.path.join("foo", "bar.shp"))

    def test_double_dot_component_resolved(self):
        """A '../' steps up one directory correctly."""
        self.assertEqual(parse_rel_path("foo/../bar.shp"), "bar.shp")

    def test_multiple_double_dots_resolved(self):
        """Multiple '..' components are all resolved in sequence."""
        self.assertEqual(parse_rel_path("a/b/c/../../d.shp"), os.path.join("a", "d.shp"))

    def test_leading_dot_slash(self):
        """A './' prefix is stripped, leaving just the filename."""
        self.assertEqual(parse_rel_path("./dem.tif"), "dem.tif")

    # ── degenerate / boundary inputs ────────────────────────────────────────

    def test_empty_string_becomes_dot(self):
        """normpath converts an empty string to '.' (current directory)."""
        self.assertEqual(parse_rel_path(""), ".")

    def test_single_dot_stays_dot(self):
        """A bare '.' stays as '.'."""
        self.assertEqual(parse_rel_path("."), ".")

    def test_double_dot_stays_double_dot(self):
        """A bare '..' stays as '..' (cannot go higher without an anchor)."""
        self.assertEqual(parse_rel_path(".."), "..")

    def test_root_path_unchanged(self):
        """The filesystem root '/' is returned unchanged."""
        self.assertEqual(parse_rel_path("/"), "/")

    # ── absolute paths ───────────────────────────────────────────────────────

    def test_absolute_unix_path_normalised(self):
        """An already-correct absolute path is preserved."""
        p = "/home/user/project/file.shp"
        self.assertEqual(parse_rel_path(p), os.path.normpath(p))

    def test_absolute_path_with_redundant_slashes(self):
        """Redundant slashes in an absolute path are collapsed."""
        self.assertEqual(parse_rel_path("/foo//bar///baz"), os.path.normpath("/foo/bar/baz"))

    def test_absolute_path_with_dot_dot(self):
        """A '..' in an absolute path is resolved upward."""
        self.assertEqual(parse_rel_path("/foo/bar/../baz"), os.path.normpath("/foo/baz"))

    # ── idempotency ──────────────────────────────────────────────────────────

    def test_already_normalised_path_is_idempotent(self):
        """Calling parse_rel_path twice returns the same result as calling it once."""
        path = "data/inputs/dem.tif"
        once = parse_rel_path(path)
        twice = parse_rel_path(once)
        self.assertEqual(once, twice)


# ── safe_make_relpath ─────────────────────────────────────────────────────────


class TestSafeMakeRelpath(unittest.TestCase):
    """safe_make_relpath(in_path, cwd_path)
    If in_path is absolute  → os.path.relpath(in_path, cwd_path)
    If in_path is relative  → returned unchanged
    """

    # ── absolute inputs: converted to relative ───────────────────────────────

    def test_direct_child_file(self):
        """An absolute child file path becomes a one-component relative path."""
        result = safe_make_relpath("/projects/myproject/dem.tif", CWD)
        self.assertEqual(result, "dem.tif")

    def test_nested_child_path(self):
        """A multi-level child path is expressed relative to cwd."""
        result = safe_make_relpath("/projects/myproject/data/dem.tif", CWD)
        self.assertEqual(result, os.path.join("data", "dem.tif"))

    def test_deeply_nested_child(self):
        """A deeply nested child is fully relativised."""
        result = safe_make_relpath("/projects/myproject/a/b/c/file.shp", CWD)
        self.assertEqual(result, os.path.join("a", "b", "c", "file.shp"))

    def test_same_directory_returns_dot(self):
        """When in_path equals cwd the result is '.' (same location)."""
        result = safe_make_relpath(CWD, CWD)
        self.assertEqual(result, ".")

    def test_parent_directory_returns_dotdot(self):
        """The direct parent of cwd is expressed as '..'."""
        result = safe_make_relpath("/projects", CWD)
        self.assertEqual(result, "..")

    def test_sibling_directory(self):
        """A sibling directory is expressed as '../sibling'."""
        result = safe_make_relpath("/projects/other", CWD)
        self.assertEqual(result, os.path.join("..", "other"))

    def test_completely_unrelated_tree(self):
        """A path in a completely different directory tree is correctly relativised."""
        result = safe_make_relpath("/completely/unrelated/path", CWD)
        self.assertEqual(result, os.path.join("..", "..", "completely", "unrelated", "path"))

    def test_result_is_never_absolute_for_absolute_input(self):
        """The returned path is always relative when the input was absolute."""
        result = safe_make_relpath("/projects/myproject/data/dem.tif", CWD)
        self.assertFalse(os.path.isabs(result))

    # ── relative inputs: passed through unchanged ────────────────────────────

    def test_simple_relative_unchanged(self):
        """A simple relative path is returned exactly as given."""
        self.assertEqual(safe_make_relpath("data/dem.tif", CWD), "data/dem.tif")

    def test_relative_with_dotdot_unchanged(self):
        """A relative path that already contains '..' is not altered."""
        self.assertEqual(safe_make_relpath("../other/file.tif", CWD), "../other/file.tif")

    def test_relative_dot_unchanged(self):
        """A bare '.' passed as a relative path is returned unchanged."""
        self.assertEqual(safe_make_relpath(".", CWD), ".")

    def test_relative_dotdot_unchanged(self):
        """A bare '..' is returned unchanged."""
        self.assertEqual(safe_make_relpath("..", CWD), "..")

    def test_empty_string_unchanged(self):
        """An empty string is not absolute, so it is returned unchanged."""
        self.assertEqual(safe_make_relpath("", CWD), "")

    def test_multi_component_relative_unchanged(self):
        """A multi-level relative path is returned byte-for-byte identical."""
        path = "inputs/topography/dem.tif"
        self.assertEqual(safe_make_relpath(path, CWD), path)


# ── safe_make_abspath ─────────────────────────────────────────────────────────


class TestSafeMakeAbspath(unittest.TestCase):
    """safe_make_abspath(in_path, cwd_path)
    If in_path is relative → os.path.abspath(os.path.join(cwd_path, in_path))
    If in_path is absolute → returned unchanged (no normalisation applied)
    """

    # ── relative inputs: resolved to absolute ────────────────────────────────

    def test_simple_relative_resolved(self):
        """A bare filename becomes an absolute path under cwd."""
        result = safe_make_abspath("dem.tif", CWD)
        self.assertEqual(result, "/projects/myproject/dem.tif")

    def test_multi_level_relative_resolved(self):
        """A multi-level relative path is fully resolved under cwd."""
        result = safe_make_abspath("data/inputs/dem.tif", CWD)
        self.assertEqual(result, "/projects/myproject/data/inputs/dem.tif")

    def test_dot_resolves_to_cwd(self):
        """A bare '.' resolves to cwd itself."""
        result = safe_make_abspath(".", CWD)
        self.assertEqual(result, CWD)

    def test_dotslash_prefix_stripped(self):
        """A './' prefix is stripped, leaving a clean absolute path."""
        result = safe_make_abspath("./data/dem.tif", CWD)
        self.assertEqual(result, "/projects/myproject/data/dem.tif")

    def test_dotdot_resolves_to_parent(self):
        """'..' steps up one level from cwd."""
        result = safe_make_abspath("..", CWD)
        self.assertEqual(result, "/projects")

    def test_multiple_dotdots_resolved(self):
        """Multiple '..' components are all resolved."""
        result = safe_make_abspath("../../other", "/projects/myproject/sub")
        self.assertEqual(result, "/projects/other")

    def test_dotdot_then_child(self):
        """Going up one level then into a sibling directory is resolved correctly."""
        result = safe_make_abspath("../sibling/file.shp", CWD)
        self.assertEqual(result, "/projects/sibling/file.shp")

    def test_empty_string_resolves_to_cwd(self):
        """An empty string is treated as a relative path and resolves to cwd."""
        result = safe_make_abspath("", CWD)
        self.assertEqual(result, CWD)

    def test_result_is_always_absolute_for_relative_input(self):
        """The result is always an absolute path when the input was relative."""
        result = safe_make_abspath("some/relative/path.tif", CWD)
        self.assertTrue(os.path.isabs(result))

    # ── absolute inputs: passed through unchanged ────────────────────────────

    def test_absolute_path_returned_unchanged(self):
        """An already-absolute path is returned as-is."""
        p = "/other/project/file.shp"
        self.assertEqual(safe_make_abspath(p, CWD), p)

    def test_absolute_root_returned_unchanged(self):
        """The filesystem root '/' is returned unchanged."""
        self.assertEqual(safe_make_abspath("/", CWD), "/")

    def test_absolute_path_with_dotdot_not_normalised(self):
        """An absolute path containing '..' is returned verbatim — the function
        does NOT normalise absolute inputs, so the '..' is preserved as-is."""
        p = "/projects/myproject/../other/file.shp"
        self.assertEqual(safe_make_abspath(p, CWD), p)

    def test_absolute_path_with_double_slash_not_normalised(self):
        """An absolute path with redundant slashes is also returned verbatim."""
        p = "/projects//myproject/file.shp"
        self.assertEqual(safe_make_abspath(p, CWD), p)

    def test_absolute_input_cwd_is_ignored(self):
        """When in_path is already absolute, the cwd argument has no effect."""
        p = "/absolute/path/file.shp"
        result_a = safe_make_abspath(p, "/cwd/a")
        result_b = safe_make_abspath(p, "/cwd/b")
        self.assertEqual(result_a, result_b)
        self.assertEqual(result_a, p)


if __name__ == "__main__":
    unittest.main()
