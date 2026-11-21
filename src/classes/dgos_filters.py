"""Filter logic for the DGOs vector tile layer.

This module intentionally does **not** import QGIS.  It only builds QGIS
expression strings, which lets the filtering rules be unit-tested without a
running QGIS application.

The filter groups map onto fields in the IGO/DGO vector tiles:

==================  ========================  ================================
Group               Field                     Values
==================  ========================  ================================
Ownership           ``ownership``             ``PVT``, ``BLM``
Stream order        ``stream_order``          ``1`` … ``5``
Stream permanence   ``fcode``                 ``46006`` Perennial,
                                              ``46003`` Intermittent,
                                              ``46007`` Ephemeral
Risk                ``brat_risk``             ``Negligible Risk``,
                                              ``Minor Risk``, ``Some Risk``
Existing capacity   ``brat_capacity``         float ``0`` … ``40`` (range)
Historic capacity   ``brat_hist_capacity``    float ``0`` … ``40`` (range)
US state            ``state``                 USPS two-letter abbreviations
==================  ========================  ================================

Within a group the selected values are combined with ``OR``; the groups are
combined with ``AND``.  An empty group contributes no clause, so an empty
selection means "show everything".  The two capacity groups are ranges: each
adds ``>= lower`` and/or ``<= upper`` clauses, and adds nothing at all while it
still spans the full ``0``-``40`` range (so NULL capacities are not hidden).
"""

from __future__ import annotations

#: Ownership values offered by the dock.
OWNERSHIP_VALUES = ("PVT", "BLM", "STATE", "UND")

#: Stream orders offered by the dock.
STREAM_ORDER_VALUES = (1, 2, 3, 4, 5)

#: Field holding the stream's NHD fcode.
PERMANENCE_FIELD = "fcode"

#: Stream permanence options as ``(label, fcode)`` pairs, in dock order.
STREAM_PERMANENCE_VALUES = (
    ("Perennial", 46006),
    ("Intermittent", 46003),
    ("Ephemeral", 46007),
)

#: Field holding the modelled BRAT risk class.
RISK_FIELD = "brat_risk"

#: Risk classes offered by the dock, in dock order.
RISK_VALUES = ("Negligible Risk", "Minor Risk", "Some Risk")

#: Field holding the modelled existing beaver capacity (a float).
CAPACITY_FIELD = "brat_capacity"

#: Field holding the modelled historic beaver capacity (a float).
HIST_CAPACITY_FIELD = "brat_hist_capacity"

#: Bounds of the capacity lower/upper controls (both capacity fields).
CAPACITY_MIN = 0
CAPACITY_MAX = 40

#: The 50 US states as ``(USPS abbreviation, display name)`` pairs.
US_STATES = (
    ("AL", "Alabama"),
    ("AK", "Alaska"),
    ("AZ", "Arizona"),
    ("AR", "Arkansas"),
    ("CA", "California"),
    ("CO", "Colorado"),
    ("CT", "Connecticut"),
    ("DE", "Delaware"),
    ("FL", "Florida"),
    ("GA", "Georgia"),
    ("HI", "Hawaii"),
    ("ID", "Idaho"),
    ("IL", "Illinois"),
    ("IN", "Indiana"),
    ("IA", "Iowa"),
    ("KS", "Kansas"),
    ("KY", "Kentucky"),
    ("LA", "Louisiana"),
    ("ME", "Maine"),
    ("MD", "Maryland"),
    ("MA", "Massachusetts"),
    ("MI", "Michigan"),
    ("MN", "Minnesota"),
    ("MS", "Mississippi"),
    ("MO", "Missouri"),
    ("MT", "Montana"),
    ("NE", "Nebraska"),
    ("NV", "Nevada"),
    ("NH", "New Hampshire"),
    ("NJ", "New Jersey"),
    ("NM", "New Mexico"),
    ("NY", "New York"),
    ("NC", "North Carolina"),
    ("ND", "North Dakota"),
    ("OH", "Ohio"),
    ("OK", "Oklahoma"),
    ("OR", "Oregon"),
    ("PA", "Pennsylvania"),
    ("RI", "Rhode Island"),
    ("SC", "South Carolina"),
    ("SD", "South Dakota"),
    ("TN", "Tennessee"),
    ("TX", "Texas"),
    ("UT", "Utah"),
    ("VT", "Vermont"),
    ("VA", "Virginia"),
    ("WA", "Washington"),
    ("WV", "West Virginia"),
    ("WI", "Wisconsin"),
    ("WY", "Wyoming"),
)

#: Just the abbreviations, in the same order as :data:`US_STATES`.
STATE_ABBREVIATIONS = tuple(abbr for abbr, _name in US_STATES)


def quote_string(value: str) -> str:
    """Return *value* as a single-quoted QGIS expression string literal.

    Embedded single quotes are escaped by doubling them, which is the
    convention QGIS expressions use.
    """
    return "'" + str(value).replace("'", "''") + "'"


def _or_string_clause(field: str, values) -> str:
    """``("field" = 'a' OR "field" = 'b')`` for the given string values."""
    parts = [f'"{field}" = {quote_string(value)}' for value in values]
    return "(" + " OR ".join(parts) + ")"


def _or_int_clause(field: str, values) -> str:
    """``(to_int("field") = 1 OR to_int("field") = 2)``.

    ``to_int`` is used so the filter also works if the tile service stores the
    value as a string instead of an integer.
    """
    parts = []
    for value in values:
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        parts.append(f'to_int("{field}") = {number}')
    return "(" + " OR ".join(parts) + ")"


def _capacity_clause(field: str, capacity_range) -> str:
    """Build a capacity range clause for *field*, or ``""`` for the full range.

    ``capacity_range`` is a ``(lower, upper)`` pair.  A bound only produces a
    clause when it actually narrows the range, so the initial 0-40 selection
    filters nothing (and therefore still shows features with a NULL capacity).
    """
    try:
        lower, upper = capacity_range
    except (TypeError, ValueError):
        return ""

    parts = []
    if lower > CAPACITY_MIN:
        parts.append(f'"{field}" >= {lower}')
    if upper < CAPACITY_MAX:
        parts.append(f'"{field}" <= {upper}')

    return "(" + " AND ".join(parts) + ")" if parts else ""


def build_filter_expression(ownerships=(), stream_orders=(), states=(), capacity_range=None, hist_capacity_range=None, permanence=(), risks=()) -> str:
    """Build a QGIS expression for the dock's filters.

    Args:
        ownerships: Selected ``ownership`` values (e.g. ``["PVT", "BLM"]``).
        stream_orders: Selected ``stream_order`` values (e.g. ``[1, 3]``).
        states: Selected USPS ``state`` abbreviations (e.g. ``["ID", "MT"]``).
        capacity_range: ``(lower, upper)`` bounds for ``brat_capacity``.
            The full ``(0, 40)`` range contributes no clause.
        hist_capacity_range: ``(lower, upper)`` bounds for
            ``brat_hist_capacity``.  The full ``(0, 40)`` range contributes no
            clause.
        permanence: Selected stream permanence ``fcode`` values (e.g.
            ``[46006, 46007]`` — see :data:`STREAM_PERMANENCE_VALUES`).
        risks: Selected ``brat_risk`` classes (e.g. ``["Minor Risk"]`` — see
            :data:`RISK_VALUES`).  ``permanence`` and ``risks`` are placed last
            so existing positional calls keep working; their clauses still land
            next to the stream-order one.

    Returns:
        A QGIS expression string.  Empty string when nothing is selected, which
        tells the renderer to show all features.
    """
    clauses = []

    if ownerships:
        clauses.append(_or_string_clause("ownership", ownerships))
    if stream_orders:
        clauses.append(_or_int_clause("stream_order", stream_orders))
    if permanence:
        clauses.append(_or_int_clause(PERMANENCE_FIELD, permanence))
    if risks:
        clauses.append(_or_string_clause(RISK_FIELD, risks))
    if capacity_range:
        capacity = _capacity_clause(CAPACITY_FIELD, capacity_range)
        if capacity:
            clauses.append(capacity)
    if hist_capacity_range:
        hist_capacity = _capacity_clause(HIST_CAPACITY_FIELD, hist_capacity_range)
        if hist_capacity:
            clauses.append(hist_capacity)
    if states:
        clauses.append(_or_string_clause("state", states))

    return " AND ".join(clauses)
