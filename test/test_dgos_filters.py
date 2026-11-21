"""Unit tests for src/classes/dgos_filters.py

These tests have no QGIS dependency — dgos_filters.py builds QGIS expression
strings using only the standard library.  They cover the filter groups
(ownership, stream order, stream permanence, state), the OR-within /
AND-between combination rules, and the "no selection means show everything"
behaviour.
"""

import os
import sys
import unittest

# Add src/classes directly so we can import dgos_filters without triggering
# src/__init__.py, which has a hard dependency on qgis.core.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "classes")))

from dgos_filters import (
    CAPACITY_FIELD,
    CAPACITY_MAX,
    CAPACITY_MIN,
    HIGH_STREAM_POWER_FIELD,
    HIST_CAPACITY_FIELD,
    HYDROLOGY_RANGES,
    LAND_USE_INTENSITY_CLASSES,
    LAND_USE_INTENSITY_FIELD,
    HUC10_FIELD,
    LEVEL_PATH_FIELD,
    LEVEL_PATH_MAX_LENGTH,
    LIMITATION_CLASSES,
    LIMITATION_FIELD,
    LOW_STREAM_POWER_FIELD,
    OWNERSHIP_VALUES,
    FLOODPLAIN_AREA_FIELD,
    GEOMORPHOLOGY_RANGES,
    GRADIENT_FIELD,
    OPPORTUNITY_FIELD,
    OPPORTUNITY_VALUES,
    PERMANENCE_FIELD,
    RAIL_DENSITY_FIELD,
    RISK_FIELD,
    RISK_VALUES,
    STATE_ABBREVIATIONS,
    STREAM_ORDER_VALUES,
    STREAM_PERMANENCE_VALUES,
    TRANSPORTATION_RANGES,
    US_STATES,
    VALLEY_BOTTOM_AREA_FIELD,
    ROAD_DENSITY_FIELD,
    build_filter_expression,
    format_number,
    quote_string,
)


class TestConstants(unittest.TestCase):
    def test_ownership_values(self):
        self.assertEqual(list(OWNERSHIP_VALUES), ["PVT", "BLM"])

    def test_stream_order_values(self):
        self.assertEqual(list(STREAM_ORDER_VALUES), [1, 2, 3, 4, 5])

    def test_fifty_unique_states(self):
        self.assertEqual(len(US_STATES), 50)
        self.assertEqual(len(STATE_ABBREVIATIONS), 50)
        self.assertEqual(len(set(STATE_ABBREVIATIONS)), 50)

    def test_state_abbreviations_are_two_uppercase_letters(self):
        for abbr in STATE_ABBREVIATIONS:
            self.assertRegex(abbr, r"^[A-Z]{2}$")

    def test_known_state_abbreviations(self):
        for abbr in ("ID", "MT", "WY", "AK", "HI", "NY", "CA"):
            self.assertIn(abbr, STATE_ABBREVIATIONS)


class TestStreamPermanence(unittest.TestCase):
    def test_values(self):
        self.assertEqual(
            list(STREAM_PERMANENCE_VALUES),
            [("Perennial", 46006), ("Intermittent", 46003), ("Ephemeral", 46007)],
        )

    def test_field(self):
        self.assertEqual(PERMANENCE_FIELD, "fcode")

    def test_single_value(self):
        self.assertEqual(
            build_filter_expression(permanence=[46006]),
            '(to_int("fcode") = 46006)',
        )

    def test_multiple_values_are_ored(self):
        self.assertEqual(
            build_filter_expression(permanence=[46006, 46007]),
            '(to_int("fcode") = 46006 OR to_int("fcode") = 46007)',
        )

    def test_combines_with_other_groups(self):
        self.assertEqual(
            build_filter_expression(permanence=[46003], states=["ID"]),
            '(to_int("fcode") = 46003) AND ("state" = \'ID\')',
        )

    def test_empty_selection_adds_no_clause(self):
        self.assertEqual(build_filter_expression(permanence=[]), "")


class TestRisk(unittest.TestCase):
    def test_values(self):
        self.assertEqual(
            list(RISK_VALUES),
            ["Negligible Risk", "Minor Risk", "Some Risk", "Considerable Risk", "None"],
        )

    def test_field(self):
        self.assertEqual(RISK_FIELD, "brat_risk")

    def test_single_value(self):
        self.assertEqual(
            build_filter_expression(risks=["Minor Risk"]),
            '("brat_risk" = \'Minor Risk\')',
        )

    def test_multiple_values_are_ored(self):
        self.assertEqual(
            build_filter_expression(risks=["Negligible Risk", "Some Risk"]),
            '("brat_risk" = \'Negligible Risk\' OR "brat_risk" = \'Some Risk\')',
        )

    def test_quotes_embedded_apostrophes(self):
        self.assertEqual(
            build_filter_expression(risks=["O'Brien Risk"]),
            '("brat_risk" = \'O\'\'Brien Risk\')',
        )

    def test_combines_with_other_groups(self):
        self.assertEqual(
            build_filter_expression(risks=["Some Risk"], states=["ID"]),
            '("brat_risk" = \'Some Risk\') AND ("state" = \'ID\')',
        )

    def test_empty_selection_adds_no_clause(self):
        self.assertEqual(build_filter_expression(risks=[]), "")

    def test_does_not_break_positional_states(self):
        self.assertEqual(
            build_filter_expression([], [], ["ID"]),
            '("state" = \'ID\')',
        )


class TestOpportunities(unittest.TestCase):
    def test_values(self):
        self.assertEqual(
            list(OPPORTUNITY_VALUES),
            [
                "Conservation/Appropriate for Translocation",
                "Encourage Beaver Expansion/Colonization",
                "Beaver Mimicry",
                "Conflict Management",
                "Land Management Change",
                "Potential Floodplain/Side Channel Opportunities",
                "Natural or Anthropogenic Limitations",
            ],
        )

    def test_field(self):
        self.assertEqual(OPPORTUNITY_FIELD, "brat_opportunity")

    def test_single_value(self):
        self.assertEqual(
            build_filter_expression(opportunities=["Beaver Mimicry"]),
            '("brat_opportunity" = \'Beaver Mimicry\')',
        )

    def test_multiple_values_are_ored(self):
        self.assertEqual(
            build_filter_expression(opportunities=["Conflict Management", "Land Management Change"]),
            '("brat_opportunity" = \'Conflict Management\' OR "brat_opportunity" = \'Land Management Change\')',
        )

    def test_combines_with_risk(self):
        self.assertEqual(
            build_filter_expression(risks=["Some Risk"], opportunities=["Beaver Mimicry"]),
            '("brat_risk" = \'Some Risk\') AND ("brat_opportunity" = \'Beaver Mimicry\')',
        )

    def test_empty_selection_adds_no_clause(self):
        self.assertEqual(build_filter_expression(opportunities=[]), "")


class TestFormatNumber(unittest.TestCase):
    def test_whole_numbers_have_no_decimal_point(self):
        self.assertEqual(format_number(3.0), "3")
        self.assertEqual(format_number(10), "10")

    def test_fractional_numbers_keep_their_precision(self):
        self.assertEqual(format_number(0.05), "0.05")
        self.assertEqual(format_number(0.005), "0.005")

    def test_unparseable_values_pass_through(self):
        self.assertEqual(format_number("already text"), "already text")


class TestGeomorphologyRanges(unittest.TestCase):
    def test_config(self):
        self.assertEqual(
            GEOMORPHOLOGY_RANGES,
            (
                ("Gradient", GRADIENT_FIELD, 0.0, 1.0, 3, 0.005),
                ("Valley Bottom Area", VALLEY_BOTTOM_AREA_FIELD, 0.0, 1000.0, 1, 5.0),
                ("Floodplain Area", FLOODPLAIN_AREA_FIELD, 0.0, 10000.0, 1, 10.0),
            ),
        )

    def test_fields(self):
        self.assertEqual(GRADIENT_FIELD, "primary_channel_gradient")
        self.assertEqual(VALLEY_BOTTOM_AREA_FIELD, "acres_vb_per_mile")
        self.assertEqual(FLOODPLAIN_AREA_FIELD, "floodplain_area")

    def test_lower_bound_only(self):
        self.assertEqual(
            build_filter_expression(range_filters=[(GRADIENT_FIELD, (0.02, 1.0), 0.0, 1.0)]),
            '("primary_channel_gradient" >= 0.02)',
        )

    def test_both_bounds(self):
        self.assertEqual(
            build_filter_expression(range_filters=[(VALLEY_BOTTOM_AREA_FIELD, (5.0, 250.0), 0.0, 1000.0)]),
            '("acres_vb_per_mile" >= 5 AND "acres_vb_per_mile" <= 250)',
        )

    def test_full_range_adds_nothing(self):
        self.assertEqual(build_filter_expression(range_filters=[(FLOODPLAIN_AREA_FIELD, (0.0, 10000.0), 0.0, 10000.0)]), "")

    def test_multiple_ranges_and_other_groups(self):
        self.assertEqual(
            build_filter_expression(
                risks=["Some Risk"],
                range_filters=[
                    (GRADIENT_FIELD, (0.005, 1.0), 0.0, 1.0),
                    (FLOODPLAIN_AREA_FIELD, (0.0, 500.0), 0.0, 10000.0),
                ],
                states=["ID"],
            ),
            '("brat_risk" = \'Some Risk\') AND ("primary_channel_gradient" >= 0.005) AND ("floodplain_area" <= 500) AND ("state" = \'ID\')',
        )

    def test_malformed_range_is_ignored(self):
        self.assertEqual(build_filter_expression(range_filters=[(GRADIENT_FIELD, None, 0.0, 1.0)]), "")


class TestTransportationRanges(unittest.TestCase):
    def test_config(self):
        self.assertEqual(
            TRANSPORTATION_RANGES,
            (
                ("Road Density", ROAD_DENSITY_FIELD, 0.0, 20.0, 2, 0.1),
                ("Rail Density", RAIL_DENSITY_FIELD, 0.0, 10.0, 2, 0.1),
            ),
        )

    def test_fields(self):
        self.assertEqual(ROAD_DENSITY_FIELD, "road_den")
        self.assertEqual(RAIL_DENSITY_FIELD, "rail_dens")

    def test_road_density_lower_bound(self):
        self.assertEqual(
            build_filter_expression(range_filters=[(ROAD_DENSITY_FIELD, (0.5, 20.0), 0.0, 20.0)]),
            '("road_den" >= 0.5)',
        )

    def test_rail_density_both_bounds(self):
        self.assertEqual(
            build_filter_expression(range_filters=[(RAIL_DENSITY_FIELD, (0.2, 5.0), 0.0, 10.0)]),
            '("rail_dens" >= 0.2 AND "rail_dens" <= 5)',
        )

    def test_full_range_adds_nothing(self):
        self.assertEqual(build_filter_expression(range_filters=[(ROAD_DENSITY_FIELD, (0.0, 20.0), 0.0, 20.0)]), "")

    def test_combines_with_geomorphology(self):
        self.assertEqual(
            build_filter_expression(
                range_filters=[
                    (GRADIENT_FIELD, (0.02, 1.0), 0.0, 1.0),
                    (ROAD_DENSITY_FIELD, (0.5, 20.0), 0.0, 20.0),
                ]
            ),
            '("primary_channel_gradient" >= 0.02) AND ("road_den" >= 0.5)',
        )


class TestHydrologyRanges(unittest.TestCase):
    def test_config(self):
        self.assertEqual(
            HYDROLOGY_RANGES,
            (
                ("High Stream Power", HIGH_STREAM_POWER_FIELD, 0.0, 20000.0, 0, 100.0),
                ("Low Stream Power", LOW_STREAM_POWER_FIELD, 0.0, 20000.0, 0, 100.0),
            ),
        )

    def test_fields(self):
        self.assertEqual(HIGH_STREAM_POWER_FIELD, "splow")
        self.assertEqual(LOW_STREAM_POWER_FIELD, "sphigh")

    def test_high_stream_power_lower_bound(self):
        self.assertEqual(
            build_filter_expression(range_filters=[(HIGH_STREAM_POWER_FIELD, (1000.0, 20000.0), 0.0, 20000.0)]),
            '("splow" >= 1000)',
        )

    def test_low_stream_power_upper_bound(self):
        self.assertEqual(
            build_filter_expression(range_filters=[(LOW_STREAM_POWER_FIELD, (0.0, 500.0), 0.0, 20000.0)]),
            '("sphigh" <= 500)',
        )

    def test_both_powers_together(self):
        self.assertEqual(
            build_filter_expression(
                range_filters=[
                    (HIGH_STREAM_POWER_FIELD, (15.0, 20000.0), 0.0, 20000.0),
                    (LOW_STREAM_POWER_FIELD, (0.0, 5000.0), 0.0, 20000.0),
                ]
            ),
            '("splow" >= 15) AND ("sphigh" <= 5000)',
        )

    def test_full_range_adds_nothing(self):
        self.assertEqual(build_filter_expression(range_filters=[(HIGH_STREAM_POWER_FIELD, (0.0, 20000.0), 0.0, 20000.0)]), "")


class TestLandUseIntensity(unittest.TestCase):
    def test_classes(self):
        self.assertEqual(
            LAND_USE_INTENSITY_CLASSES,
            (("Low", 0.0, 33.0), ("Medium", 33.0, 66.0), ("High", 66.0, 100.0)),
        )

    def test_field(self):
        self.assertEqual(LAND_USE_INTENSITY_FIELD, "land_use_intens")

    def test_low_class(self):
        self.assertEqual(
            build_filter_expression(land_use=[(0.0, 33.0)]),
            '("land_use_intens" >= 0 AND "land_use_intens" < 33)',
        )

    def test_middle_class(self):
        self.assertEqual(
            build_filter_expression(land_use=[(33.0, 66.0)]),
            '("land_use_intens" >= 33 AND "land_use_intens" < 66)',
        )

    def test_top_class_is_inclusive(self):
        self.assertEqual(
            build_filter_expression(land_use=[(66.0, 100.0)]),
            '("land_use_intens" >= 66 AND "land_use_intens" <= 100)',
        )

    def test_classes_are_ored(self):
        self.assertEqual(
            build_filter_expression(land_use=[(0.0, 33.0), (66.0, 100.0)]),
            '("land_use_intens" >= 0 AND "land_use_intens" < 33 OR "land_use_intens" >= 66 AND "land_use_intens" <= 100)',
        )

    def test_combines_with_ownership(self):
        self.assertEqual(
            build_filter_expression(ownerships=["BLM"], land_use=[(33.0, 66.0)]),
            '("ownership" = \'BLM\') AND ("land_use_intens" >= 33 AND "land_use_intens" < 66)',
        )

    def test_empty_selection_adds_no_clause(self):
        self.assertEqual(build_filter_expression(land_use=[]), "")


class TestLimitations(unittest.TestCase):
    def test_classes(self):
        self.assertEqual(len(LIMITATION_CLASSES), 8)
        self.assertEqual(LIMITATION_CLASSES[0], ("Anthropogenically Limited", "Anthropogenically Limited"))
        self.assertEqual(LIMITATION_CLASSES[2], ("Slope Limited", "Slope Limited"))
        self.assertEqual(LIMITATION_CLASSES[6], ("Dam Building Possible", "Dam Building Possible"))
        self.assertEqual(LIMITATION_CLASSES[7], ("Other", None))

    def test_field(self):
        self.assertEqual(LIMITATION_FIELD, "brat_limitation")

    def test_single_class(self):
        self.assertEqual(
            build_filter_expression(limitations=["Stream Power Limited"]),
            '("brat_limitation" = \'Stream Power Limited\')',
        )

    def test_other_class_means_null(self):
        self.assertEqual(
            build_filter_expression(limitations=[None]),
            '("brat_limitation" IS NULL OR "brat_limitation" = \'\')',
        )

    def test_classes_are_ored(self):
        self.assertEqual(
            build_filter_expression(limitations=["Slope Limited", "Stream Size Limited"]),
            '("brat_limitation" = \'Slope Limited\' OR "brat_limitation" = \'Stream Size Limited\')',
        )

    def test_combines_with_risk(self):
        self.assertEqual(
            build_filter_expression(risks=["Some Risk"], limitations=["Slope Limited"]),
            '("brat_risk" = \'Some Risk\') AND ("brat_limitation" = \'Slope Limited\')',
        )

    def test_empty_selection_adds_no_clause(self):
        self.assertEqual(build_filter_expression(limitations=[]), "")


class TestLevelPath(unittest.TestCase):
    def test_field_and_length(self):
        self.assertEqual(LEVEL_PATH_FIELD, "level_path")
        self.assertEqual(LEVEL_PATH_MAX_LENGTH, 128)

    def test_substring_match(self):
        self.assertEqual(
            build_filter_expression(level_path="1.2.3"),
            'strpos("level_path", \'1.2.3\') > 0',
        )

    def test_quotes_are_escaped(self):
        self.assertEqual(
            build_filter_expression(level_path="O'Brien"),
            'strpos("level_path", \'O\'\'Brien\') > 0',
        )

    def test_combines_with_other_groups(self):
        self.assertEqual(
            build_filter_expression(level_path="9.8", states=["ID"]),
            'strpos("level_path", \'9.8\') > 0 AND ("state" = \'ID\')',
        )

    def test_blank_text_adds_no_clause(self):
        self.assertEqual(build_filter_expression(level_path=""), "")


class TestHuc10(unittest.TestCase):
    def test_field(self):
        self.assertEqual(HUC10_FIELD, "huc10")

    def test_substring_match(self):
        self.assertEqual(
            build_filter_expression(huc10="17040212"),
            'strpos("huc10", \'17040212\') > 0',
        )

    def test_combines_with_level_path(self):
        self.assertEqual(
            build_filter_expression(level_path="1.2", huc10="1704"),
            'strpos("level_path", \'1.2\') > 0 AND strpos("huc10", \'1704\') > 0',
        )

    def test_quotes_are_escaped(self):
        self.assertEqual(
            build_filter_expression(huc10="O'Brien"),
            'strpos("huc10", \'O\'\'Brien\') > 0',
        )

    def test_blank_text_adds_no_clause(self):
        self.assertEqual(build_filter_expression(huc10=""), "")


class TestQuoteString(unittest.TestCase):
    def test_wraps_in_single_quotes(self):
        self.assertEqual(quote_string("PVT"), "'PVT'")

    def test_escapes_embedded_quote(self):
        self.assertEqual(quote_string("O'Brien"), "'O''Brien'")


class TestBuildFilterExpression(unittest.TestCase):
    def test_no_selection_is_empty(self):
        """No selections means no filter, i.e. every feature is shown."""
        self.assertEqual(build_filter_expression(), "")

    def test_none_ownership_means_null_or_blank(self):
        """The symbology's "Other" bucket has no value, so it means NULL."""
        self.assertEqual(
            build_filter_expression(ownerships=[None]),
            '("ownership" IS NULL OR "ownership" = \'\')',
        )

    def test_none_ownership_combined_with_codes(self):
        self.assertEqual(
            build_filter_expression(ownerships=["BLM", None]),
            '("ownership" = \'BLM\' OR "ownership" IS NULL OR "ownership" = \'\')',
        )

    def test_single_ownership(self):
        self.assertEqual(build_filter_expression(["PVT"]), "(\"ownership\" = 'PVT')")

    def test_multiple_ownerships_are_ored(self):
        self.assertEqual(
            build_filter_expression(["PVT", "BLM"]),
            "(\"ownership\" = 'PVT' OR \"ownership\" = 'BLM')",
        )

    def test_stream_order_uses_to_int(self):
        self.assertEqual(build_filter_expression([], [3]), '(to_int("stream_order") = 3)')

    def test_multiple_stream_orders_are_ored(self):
        self.assertEqual(
            build_filter_expression([], [1, 5]),
            '(to_int("stream_order") = 1 OR to_int("stream_order") = 5)',
        )

    def test_states_are_ored(self):
        self.assertEqual(
            build_filter_expression([], [], ["ID", "MT"]),
            "(\"state\" = 'ID' OR \"state\" = 'MT')",
        )

    def test_groups_are_anded_in_order(self):
        self.assertEqual(
            build_filter_expression(["PVT"], [2], ["ID"]),
            '("ownership" = \'PVT\') AND (to_int("stream_order") = 2) AND ("state" = \'ID\')',
        )

    def test_all_groups_with_multiple_values(self):
        expression = build_filter_expression(["PVT", "BLM"], [1, 2], ["ID", "MT"])
        self.assertEqual(
            expression,
            '("ownership" = \'PVT\' OR "ownership" = \'BLM\') AND (to_int("stream_order") = 1 OR to_int("stream_order") = 2) AND ("state" = \'ID\' OR "state" = \'MT\')',
        )

    def test_missing_group_contributes_nothing(self):
        """Filtering on state alone must not add ownership/order clauses."""
        expression = build_filter_expression([], [], ["ID"])
        self.assertNotIn("ownership", expression)
        self.assertNotIn("stream_order", expression)


class TestCapacityFilter(unittest.TestCase):
    """The beaver-capacity lower/upper bounds (field ``brat_capacity``, 0-40)."""

    def test_field_and_bounds(self):
        self.assertEqual(CAPACITY_FIELD, "brat_capacity")
        self.assertEqual((CAPACITY_MIN, CAPACITY_MAX), (0, 40))

    def test_full_range_adds_no_clause(self):
        """Initialised at 0-40, the bounds filter nothing (NULLs still shown)."""
        self.assertEqual(build_filter_expression(capacity_range=(0, 40)), "")

    def test_no_capacity_range_adds_no_clause(self):
        self.assertEqual(build_filter_expression(), "")

    def test_upper_bound_only(self):
        self.assertEqual(build_filter_expression(capacity_range=(0, 20)), '("brat_capacity" <= 20)')

    def test_lower_bound_only(self):
        self.assertEqual(build_filter_expression(capacity_range=(10, 40)), '("brat_capacity" >= 10)')

    def test_both_bounds(self):
        self.assertEqual(
            build_filter_expression(capacity_range=(10, 20)),
            '("brat_capacity" >= 10 AND "brat_capacity" <= 20)',
        )

    def test_single_value_at_minimum(self):
        self.assertEqual(build_filter_expression(capacity_range=(0, 0)), '("brat_capacity" <= 0)')

    def test_single_value_at_maximum(self):
        self.assertEqual(build_filter_expression(capacity_range=(40, 40)), '("brat_capacity" >= 40)')

    def test_capacity_combines_with_other_filters_using_and(self):
        expression = build_filter_expression(["PVT"], [2], ["ID"], capacity_range=(5, 15))
        self.assertEqual(
            expression,
            '("ownership" = \'PVT\') AND (to_int("stream_order") = 2) AND ("brat_capacity" >= 5 AND "brat_capacity" <= 15) AND ("state" = \'ID\')',
        )

    def test_capacity_alone_with_other_groups_empty(self):
        expression = build_filter_expression([], [], [], capacity_range=(5, 15))
        self.assertEqual(expression, '("brat_capacity" >= 5 AND "brat_capacity" <= 15)')


class TestHistoricCapacityFilter(unittest.TestCase):
    """The historic beaver-capacity bounds (field ``brat_hist_capacity``)."""

    def test_field(self):
        self.assertEqual(HIST_CAPACITY_FIELD, "brat_hist_capacity")

    def test_full_range_adds_no_clause(self):
        self.assertEqual(build_filter_expression(hist_capacity_range=(0, 40)), "")

    def test_upper_bound_only(self):
        self.assertEqual(build_filter_expression(hist_capacity_range=(0, 20)), '("brat_hist_capacity" <= 20)')

    def test_lower_bound_only(self):
        self.assertEqual(build_filter_expression(hist_capacity_range=(10, 40)), '("brat_hist_capacity" >= 10)')

    def test_both_bounds(self):
        self.assertEqual(
            build_filter_expression(hist_capacity_range=(10, 20)),
            '("brat_hist_capacity" >= 10 AND "brat_hist_capacity" <= 20)',
        )

    def test_both_capacity_filters_are_independent_and_anded(self):
        expression = build_filter_expression(capacity_range=(5, 15), hist_capacity_range=(20, 30))
        self.assertEqual(
            expression,
            '("brat_capacity" >= 5 AND "brat_capacity" <= 15) AND ("brat_hist_capacity" >= 20 AND "brat_hist_capacity" <= 30)',
        )

    def test_historic_capacity_combined_with_all_other_filters(self):
        expression = build_filter_expression(["PVT"], [2], ["ID"], capacity_range=(5, 15), hist_capacity_range=(0, 8))
        self.assertEqual(
            expression,
            '("ownership" = \'PVT\') AND (to_int("stream_order") = 2) AND ("brat_capacity" >= 5 AND "brat_capacity" <= 15) AND ("brat_hist_capacity" <= 8) AND ("state" = \'ID\')',
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
