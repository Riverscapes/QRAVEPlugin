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
    HIST_CAPACITY_FIELD,
    OWNERSHIP_VALUES,
    PERMANENCE_FIELD,
    RISK_FIELD,
    RISK_VALUES,
    STATE_ABBREVIATIONS,
    STREAM_ORDER_VALUES,
    STREAM_PERMANENCE_VALUES,
    US_STATES,
    build_filter_expression,
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
        self.assertEqual(list(RISK_VALUES), ["Negligible Risk", "Minor Risk", "Some Risk"])

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


class TestQuoteString(unittest.TestCase):
    def test_wraps_in_single_quotes(self):
        self.assertEqual(quote_string("PVT"), "'PVT'")

    def test_escapes_embedded_quote(self):
        self.assertEqual(quote_string("O'Brien"), "'O''Brien'")


class TestBuildFilterExpression(unittest.TestCase):
    def test_no_selection_is_empty(self):
        """No selections means no filter, i.e. every feature is shown."""
        self.assertEqual(build_filter_expression(), "")

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
