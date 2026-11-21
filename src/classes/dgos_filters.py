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
Stream power        ``splow`` / ``sphigh``    float ``0`` … ``20000`` (watts)
Level path          ``level_path``            free text, 128 characters
                                              (substring match)
HUC 10              ``huc10``                 free text (substring match)
Stream permanence   ``fcode``                 ``46006`` Perennial,
                                              ``46003`` Intermittent,
                                              ``46007`` Ephemeral
Risk                ``brat_risk``             ``Negligible Risk``,
                                              ``Minor Risk``, ``Some Risk``,
                                              ``Considerable Risk``, ``None``
Limitations         ``brat_limitation``       eight BRAT limitation classes
                                              (see ``LIMITATION_CLASSES``)
Opportunities       ``brat_opportunity``      the seven BRAT opportunity
                                              classes in ``OPPORTUNITY_VALUES``
Existing capacity   ``brat_capacity``         float ``0`` … ``40`` (range)
Historic capacity   ``brat_hist_capacity``    float ``0`` … ``40`` (range)
Road density        ``road_den``              float ``0`` … ``20`` (range)
Rail density        ``rail_dens``             float ``0`` … ``10`` (range)
Land use intensity  ``land_use_intens``       ``Low`` (0-33), ``Medium``
                                              (33-66), ``High`` (66-100)
US state            ``state``                 USPS two-letter abbreviations
==================  ========================  ================================

Within a group the selected values are combined with ``OR``; the groups are
combined with ``AND``.  An empty group contributes no clause, so an empty
selection means "show everything".  The two capacity groups are ranges: each
adds ``>= lower`` and/or ``<= upper`` clauses, and adds nothing at all while it
still spans the full ``0``-``40`` range (so NULL capacities are not hidden).
"""

from __future__ import annotations

#: Field holding the land ownership class.
OWNERSHIP_FIELD = "ownership"

#: Ownership values offered by the dock.
OWNERSHIP_VALUES = ("PVT", "BLM", "STATE", "UND")

#: Field holding the stream order.
STREAM_ORDER_FIELD = "stream_order"

#: Stream orders offered by the dock.
STREAM_ORDER_VALUES = (1, 2, 3, 4, 5)

#: Field holding the USPS two-letter state abbreviation.
STATE_FIELD = "state"

#: Field holding the stream network level path.
LEVEL_PATH_FIELD = "level_path"

#: Maximum length of the level path text filter (the field's own width).
LEVEL_PATH_MAX_LENGTH = 128

#: Field holding the HUC 10 watershed code.
HUC10_FIELD = "huc10"

#: Field holding the stream's NHD fcode.
PERMANENCE_FIELD = "fcode"

#: Stream permanence options as ``(label, fcode)`` pairs, in dock order.
STREAM_PERMANENCE_VALUES = (
    ("Perennial", 46006),
    ("Intermittent", 46003),
    ("Ephemeral", 46007),
)

#: Field holding the baseflow (low) stream power, in watts.
HIGH_STREAM_POWER_FIELD = "splow"

#: Field holding the flood (high) stream power, in watts.
LOW_STREAM_POWER_FIELD = "sphigh"

#: Field holding the primary channel gradient (a fraction, e.g. ``0.02``).
GRADIENT_FIELD = "primary_channel_gradient"

#: Field holding the valley bottom area per mile (acres/mi).
VALLEY_BOTTOM_AREA_FIELD = "acres_vb_per_mile"

#: Field holding the floodplain area.
FLOODPLAIN_AREA_FIELD = "floodplain_area"

#: Field holding the land use intensity (a percentage, 0-100).
LAND_USE_INTENSITY_FIELD = "land_use_intens"

#: Land use intensity classes as ``(label, lower, upper)``.  The breaks mirror
#: the "RME - Land Use Intensity" symbology
#: (``resources/symbology/Shared/lui_rme3.qml``): 0-33, 33-66, 66-100, with the
#: top bound inclusive.  ``test_symbology_library`` checks the two stay in sync.
LAND_USE_INTENSITY_CLASSES = (
    ("Low", 0.0, 33.0),
    ("Medium", 33.0, 66.0),
    ("High", 66.0, 100.0),
)

#: Field holding the road density (km of road per km²).
ROAD_DENSITY_FIELD = "road_den"

#: Field holding the rail density (km of rail per km²).
RAIL_DENSITY_FIELD = "rail_dens"

#: Field holding the modelled BRAT risk class.
RISK_FIELD = "brat_risk"

#: Risk classes offered by the dock, in dock order.
RISK_VALUES = ("Negligible Risk", "Minor Risk", "Some Risk", "Considerable Risk", "None")

#: Geomorphology range filters, as
#: ``(label, field, minimum, maximum, decimals, step)``.  Gradient is a
#: fraction, so it needs decimals; the two area fields run much larger.
#: These bounds are also what makes an untouched control filter nothing.
GEOMORPHOLOGY_RANGES = (
    ("Gradient", GRADIENT_FIELD, 0.0, 1.0, 3, 0.005),
    ("Valley Bottom Area", VALLEY_BOTTOM_AREA_FIELD, 0.0, 1000.0, 1, 5.0),
    ("Floodplain Area", FLOODPLAIN_AREA_FIELD, 0.0, 10000.0, 1, 10.0),
)

#: Hydrology range filters, same shape as :data:`GEOMORPHOLOGY_RANGES`.
#: Stream power is in watts; the symbology classes top out at 5000.
HYDROLOGY_RANGES = (
    ("High Stream Power", HIGH_STREAM_POWER_FIELD, 0.0, 20000.0, 0, 100.0),
    ("Low Stream Power", LOW_STREAM_POWER_FIELD, 0.0, 20000.0, 0, 100.0),
)

#: Transportation range filters, same shape as :data:`GEOMORPHOLOGY_RANGES`.
#: Densities are km per km², so two decimals are enough.
TRANSPORTATION_RANGES = (
    ("Road Density", ROAD_DENSITY_FIELD, 0.0, 20.0, 2, 0.1),
    ("Rail Density", RAIL_DENSITY_FIELD, 0.0, 10.0, 2, 0.1),
)

#: Field holding the modelled BRAT limitation classes.
LIMITATION_FIELD = "brat_limitation"

#: BRAT limitation classes as ``(label, value)`` pairs, in symbology order.
#: These mirror ``brat_limitation_rme3.qml``; ``test_symbology_library`` fails
#: if the two drift apart.  The value is what the layer stores, so the list can
#: show the same strings the legend does.
LIMITATION_CLASSES = (
    ("Anthropogenically Limited", "Anthropogenically Limited"),
    ("Stream Power Limited", "Stream Power Limited"),
    ("Slope Limited", "Slope Limited"),
    ("Potential Reservoir or Land Use Change", "Potential Reservoir or Land Use Change"),
    ("Naturally Vegetation Limited", "Naturally Vegetation Limited"),
    ("Stream Size Limited", "Stream Size Limited"),
    ("Dam Building Possible", "Dam Building Possible"),
    ("Other", None),
)

#: Field holding the modelled restoration/conservation opportunity classes.
OPPORTUNITY_FIELD = "brat_opportunity"

#: Opportunity classes offered by the dock, in dock order.
OPPORTUNITY_VALUES = (
    "Conservation/Appropriate for Translocation",
    "Encourage Beaver Expansion/Colonization",
    "Beaver Mimicry",
    "Conflict Management",
    "Land Management Change",
    "Potential Floodplain/Side Channel Opportunities",
    "Natural or Anthropogenic Limitations",
)

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
    """``("field" = 'a' OR "field" = 'b')`` for the given string values.

    A ``None`` value means the field is NULL (or blank), which is how the
    symbology's "Other" category is expressed.
    """
    parts = []
    for value in values:
        if value is None:
            # No extra parentheses: the whole OR group is wrapped below.
            parts.append(f'"{field}" IS NULL OR "{field}" = \'\'')
        else:
            parts.append(f'"{field}" = {quote_string(value)}')
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


def format_number(value) -> str:
    """Render a bound as a compact QGIS literal (``3`` rather than ``3.0``)."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number == int(number):
        return str(int(number))
    return f"{number:g}"


def _range_clause(field: str, bounds, minimum: float, maximum: float) -> str:
    """Build a range clause for *field*, or ``""`` when it spans the full range.

    A bound only produces a clause when it actually narrows the range, so a
    control left at its default bounds filters nothing (and therefore still
    shows features with a NULL value).
    """
    try:
        lower, upper = bounds
    except (TypeError, ValueError):
        return ""

    parts = []
    if lower > minimum:
        parts.append(f'"{field}" >= {format_number(lower)}')
    if upper < maximum:
        parts.append(f'"{field}" <= {format_number(upper)}')

    return "(" + " AND ".join(parts) + ")" if parts else ""


def _capacity_clause(field: str, capacity_range) -> str:
    """Build a capacity range clause for *field* (bounds ``0``-``40``)."""
    return _range_clause(field, capacity_range, CAPACITY_MIN, CAPACITY_MAX)


def _class_clause(field: str, bounds, top: float | None) -> str:
    """One numeric class clause; the class holding *top* is closed on the right."""
    lower, upper = bounds
    operator = "<=" if top is not None and upper >= top else "<"
    return f'"{field}" >= {format_number(lower)} AND "{field}" {operator} {format_number(upper)}'


def build_filter_expression(
    ownerships=(),
    stream_orders=(),
    states=(),
    capacity_range=None,
    hist_capacity_range=None,
    permanence=(),
    risks=(),
    opportunities=(),
    range_filters=(),
    land_use=(),
    limitations=(),
    level_path="",
    huc10="",
) -> str:
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
            :data:`RISK_VALUES`).
        opportunities: Selected ``brat_opportunity`` classes (e.g.
            ``["Beaver Mimicry"]`` — see :data:`OPPORTUNITY_VALUES`).
        range_filters: Extra numeric range filters, each a
            ``(field, (lower, upper), minimum, maximum)`` tuple.  Bounds equal
            to *minimum*/*maximum* contribute no clause, so an untouched range
            control filters nothing.
        land_use: Selected land use intensity classes, as ``(lower, upper)``
            tuples taken from :data:`LAND_USE_INTENSITY_CLASSES`.  The classes
            are OR'd and filtered on ``land_use_intens``.
        limitations: Selected ``brat_limitation`` classes, as the values from
            :data:`LIMITATION_CLASSES` (``None`` means the "Other" bucket).
        level_path: Text typed into the level path filter.  Matched as a
            substring of ``level_path``; blank means no clause.
        huc10: Text typed into the HUC 10 filter.  Matched as a substring of
            ``huc10``; blank means no clause.
        ``permanence``, ``risks``, ``opportunities``, ``range_filters``,
            ``land_use``, ``limitations``, ``level_path`` and ``huc10`` are
            placed last so existing positional calls keep working; their
            clauses still land next to the stream-order one.

    Returns:
        A QGIS expression string.  Empty string when nothing is selected, which
        tells the renderer to show all features.
    """
    clauses = []

    if ownerships:
        clauses.append(_or_string_clause(OWNERSHIP_FIELD, ownerships))
    if stream_orders:
        clauses.append(_or_int_clause(STREAM_ORDER_FIELD, stream_orders))
    if permanence:
        clauses.append(_or_int_clause(PERMANENCE_FIELD, permanence))
    if risks:
        clauses.append(_or_string_clause(RISK_FIELD, risks))
    if opportunities:
        clauses.append(_or_string_clause(OPPORTUNITY_FIELD, opportunities))
    if land_use:
        top = max(upper for _label, _lower, upper in LAND_USE_INTENSITY_CLASSES)
        classes = [_class_clause(LAND_USE_INTENSITY_FIELD, bounds, top) for bounds in land_use]
        clauses.append("(" + " OR ".join(classes) + ")")
    if limitations:
        clauses.append(_or_string_clause(LIMITATION_FIELD, limitations))
    if level_path:
        # ``strpos`` gives a "contains" match without the user having to think
        # about SQL wildcards.
        clauses.append(f'strpos("{LEVEL_PATH_FIELD}", {quote_string(level_path)}) > 0')
    if huc10:
        clauses.append(f'strpos("{HUC10_FIELD}", {quote_string(huc10)}) > 0')
    if capacity_range:
        capacity = _capacity_clause(CAPACITY_FIELD, capacity_range)
        if capacity:
            clauses.append(capacity)
    if hist_capacity_range:
        hist_capacity = _capacity_clause(HIST_CAPACITY_FIELD, hist_capacity_range)
        if hist_capacity:
            clauses.append(hist_capacity)
    for field, bounds, minimum, maximum in range_filters:
        clause = _range_clause(field, bounds, minimum, maximum)
        if clause:
            clauses.append(clause)
    if states:
        clauses.append(_or_string_clause(STATE_FIELD, states))

    return " AND ".join(clauses)
