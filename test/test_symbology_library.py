"""Unit tests for src/classes/symbology_library.py

Like the filter tests these need no QGIS: the module only reads the business
logic XML and the QML files that ship in ``resources/``.  They cover the
business-logic layer discovery, the QML search precedence and the three QML
renderer shapes the metric engine actually uses (categorized, graduated and
rule-based), plus the single-symbol fallback.
"""

import os
import re
import sys
import unittest

# Add src/classes directly so we can import symbology_library without triggering
# src/__init__.py, which has a hard dependency on qgis.core.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "classes")))

import symbology_library as sl

HEX_COLOUR = re.compile(r"^#[0-9a-f]{6}$")


class TestBusinessLogic(unittest.TestCase):
    def test_finds_metric_engine_business_logic(self):
        path = sl.business_logic_path()
        self.assertIsNotNone(path)
        self.assertEqual(os.path.basename(path), "rs_metric_engine.xml")
        self.assertTrue(os.path.isfile(path))

    def test_unknown_project_type_is_none(self):
        self.assertIsNone(sl.business_logic_path("no_such_project_type"))

    def test_entries_are_unique_and_usable(self):
        entries = sl.load_symbology_entries()
        self.assertGreater(len(entries), 50)
        self.assertEqual(len(entries), len({entry.label for entry in entries}))

        for entry in entries:
            self.assertTrue(entry.point_qml or entry.polygon_qml, entry.label)
            for path in (entry.point_qml, entry.polygon_qml):
                if path is not None:
                    self.assertTrue(os.path.isfile(path), path)

    def test_point_and_polygon_variants_are_grouped(self):
        entries = {entry.label: entry for entry in sl.load_symbology_entries()}
        ownership = next(entry for label, entry in entries.items() if label.startswith("Dominant Land Ownership (ownership_rme3"))
        self.assertTrue(ownership.point_qml.endswith("ownership_rme3.qml"))
        self.assertTrue(ownership.polygon_qml.endswith("ownership_rme3_dgo.qml"))

        # The geometry-matched file wins, the sibling is the fallback.
        self.assertTrue(ownership.qml_for(True).endswith("ownership_rme3.qml"))
        self.assertTrue(ownership.qml_for(False).endswith("ownership_rme3_dgo.qml"))

    def test_geometry_specific_entry_falls_back_to_sibling(self):
        entry = sl.SymbologyEntry(label="x", point_qml="/tmp/point.qml", polygon_qml=None)
        self.assertEqual(entry.qml_for(True), "/tmp/point.qml")
        self.assertEqual(entry.qml_for(False), "/tmp/point.qml")


class TestFindQml(unittest.TestCase):
    def test_resolves_shared_folder(self):
        self.assertTrue(sl.find_qml("ownership_rme3").endswith(os.path.join("Shared", "ownership_rme3.qml")))

    def test_missing_name_is_none(self):
        self.assertIsNone(sl.find_qml("definitely_not_a_qml_file"))


class TestColours(unittest.TestCase):
    def test_hex(self):
        self.assertEqual(sl._normalise_colour("#AABBCC"), "#aabbcc")

    def test_rgba_string(self):
        self.assertEqual(sl._normalise_colour("255,181,84,255,rgb:1,0.7098,0.3294,1"), "#ffb554")

    def test_expression_is_rejected(self):
        self.assertIsNone(sl._normalise_colour("@symbol_color"))

    def test_darken(self):
        self.assertEqual(sl._darken("#ffffff", 0.5), "#7f7f7f")


class TestCategorizedQml(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.style = sl.parse_qml(sl.find_qml("ownership_rme3_dgo"))

    def test_renderer_type_and_field(self):
        self.assertEqual(self.style.renderer_type, "categorizedSymbol")
        self.assertEqual(self.style.attr, "ownership")

    def test_classes_and_colours(self):
        self.assertGreaterEqual(len(self.style.classes), 5)
        first = self.style.classes[0]
        self.assertEqual(first.label, "Bureau of Indian Affairs")
        self.assertEqual(first.filter_expression, "\"ownership\" = 'BIA'")
        self.assertRegex(first.fill, HEX_COLOUR)
        self.assertRegex(first.outline, HEX_COLOUR)

    def test_legend_matches_classes(self):
        self.assertEqual(self.style.legend, tuple((item.label, item.fill) for item in self.style.classes))


class TestGraduatedQml(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.style = sl.parse_qml(sl.find_qml("brat_capacity_rme3"))

    def test_renderer_type_and_field(self):
        self.assertEqual(self.style.renderer_type, "graduatedSymbol")
        self.assertEqual(self.style.attr, "brat_capacity")

    def test_ranges_become_filters(self):
        self.assertGreaterEqual(len(self.style.classes), 3)
        for symbology_class in self.style.classes:
            self.assertIn('"brat_capacity" >=', symbology_class.filter_expression)
            self.assertRegex(symbology_class.fill, HEX_COLOUR)

    def test_zero_width_ranges_are_dropped(self):
        for symbology_class in self.style.classes:
            self.assertNotRegex(symbology_class.filter_expression, r">= 0 AND \"brat_capacity\" < 0$")

    def test_top_range_is_inclusive(self):
        self.assertTrue(any("<=" in symbology_class.filter_expression for symbology_class in self.style.classes))


class TestRuleQml(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.style = sl.parse_qml(sl.find_qml("stream_order_rme3"))

    def test_renderer_type(self):
        self.assertEqual(self.style.renderer_type, "RuleRenderer")

    def test_rule_filters_are_expressions(self):
        filters = [symbology_class.filter_expression for symbology_class in self.style.classes]
        self.assertIn('"stream_order" = 1', filters)
        self.assertGreaterEqual(len(filters), 5)
        self.assertTrue(all(HEX_COLOUR.match(symbology_class.fill) for symbology_class in self.style.classes))


class TestSingleSymbolFallback(unittest.TestCase):
    def test_single_symbol_qml(self):
        style = sl.parse_qml(sl.find_qml("AOI"))
        self.assertEqual(len(style.classes), 1)
        self.assertEqual(style.classes[0].filter_expression, "")
        self.assertRegex(style.classes[0].fill, HEX_COLOUR)


if __name__ == "__main__":
    unittest.main()