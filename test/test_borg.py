"""Unit tests for src/classes/borg.py

Borg is a pure-Python shared-state pattern with no QGIS dependency.

The Borg idiom makes all instances share the same __dict__ by pointing
every instance's __dict__ at the class-level _shared_state dict.  Key
behaviours tested:

  1. Dict identity      - __dict__ is literally the same object on every instance
  2. Attribute sharing  - writes on one instance are immediately visible on all others
  3. Deletion           - deleting on one removes the attribute everywhere
  4. Persistence        - state survives the garbage-collection of the instance that wrote it
  5. Subclass sharing   - subclasses inherit _shared_state from Borg, so they share
                          state with Borg instances and with each other by default
  6. Guard pattern      - the "if key not in self.__dict__" idiom used by BaseMaps
                          initialises a field exactly once no matter how many times
                          __init__ is called

IMPORTANT: setUp/tearDown clear Borg._shared_state in-place before and
after every test so that one test cannot pollute the next.
"""

import os
import sys
import unittest

# Add src/classes directly so we can import borg without triggering
# src/__init__.py, which has a hard dependency on qgis.core.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "classes")))

from borg import Borg

# ---------------------------------------------------------------------------
# Helpers: two minimal concrete subclasses used throughout the suite.
# They deliberately do NOT define their own _shared_state, which means they
# both inherit Borg._shared_state - the default behaviour in this codebase.
# ---------------------------------------------------------------------------


class _SubA(Borg):
    """Minimal subclass A."""

    def __init__(self, **kwargs):
        Borg.__init__(self)
        for key, value in kwargs.items():
            setattr(self, key, value)


class _SubB(Borg):
    """Minimal subclass B (distinct type from _SubA)."""

    def __init__(self):
        Borg.__init__(self)


# ── Basic Borg instances ──────────────────────────────────────────────────────


class TestBorgDictIdentity(unittest.TestCase):
    """The __dict__ of every Borg instance must be the exact same object."""

    def setUp(self):
        Borg._shared_state.clear()

    def tearDown(self):
        Borg._shared_state.clear()

    def test_two_instances_share_same_dict_object(self):
        """b1.__dict__ is b2.__dict__ (identity, not merely equality)."""
        b1 = Borg()
        b2 = Borg()
        self.assertIs(b1.__dict__, b2.__dict__)

    def test_instance_dict_is_class_shared_state(self):
        """b.__dict__ is the same object as the class-level _shared_state."""
        b = Borg()
        self.assertIs(b.__dict__, Borg._shared_state)

    def test_three_instances_all_share_same_dict(self):
        """The invariant holds for any number of concurrent instances."""
        b1 = Borg()
        b2 = Borg()
        b3 = Borg()
        self.assertIs(b1.__dict__, b2.__dict__)
        self.assertIs(b2.__dict__, b3.__dict__)

    def test_shared_state_is_empty_after_clear(self):
        """After setUp, no custom attribute is present on a new instance."""
        b = Borg()
        self.assertNotIn("arbitrary_sentinel", b.__dict__)


# ── Attribute propagation ─────────────────────────────────────────────────────


class TestBorgAttributePropagation(unittest.TestCase):
    def setUp(self):
        Borg._shared_state.clear()

    def tearDown(self):
        Borg._shared_state.clear()

    def test_attribute_written_on_first_visible_on_second(self):
        """b1.x = v is immediately visible as b2.x."""
        b1 = Borg()
        b2 = Borg()
        b1.value = 42
        self.assertEqual(b2.value, 42)

    def test_attribute_written_on_second_visible_on_first(self):
        """Propagation is bidirectional."""
        b1 = Borg()
        b2 = Borg()
        b2.name = "hello"
        self.assertEqual(b1.name, "hello")

    def test_overwrite_on_one_updates_all(self):
        """Overwriting on one instance updates the shared value everywhere."""
        b1 = Borg()
        b2 = Borg()
        b1.counter = 1
        b2.counter = 99
        self.assertEqual(b1.counter, 99)

    def test_multiple_attributes_coexist(self):
        """Multiple attributes written on different instances all coexist."""
        b1 = Borg()
        b2 = Borg()
        b1.x = 1
        b2.y = 2
        b1.z = 3
        self.assertEqual(b2.x, 1)
        self.assertEqual(b1.y, 2)
        self.assertEqual(b2.z, 3)

    def test_attribute_value_types_preserved(self):
        """The shared state preserves various Python types accurately."""
        b1 = Borg()
        b2 = Borg()
        b1.integer = 7
        b1.floating = 3.14
        b1.string = "riverscapes"
        b1.lst = [1, 2, 3]
        b1.mapping = {"key": "val"}
        b1.flag = True
        b1.nothing = None
        self.assertEqual(b2.integer, 7)
        self.assertAlmostEqual(b2.floating, 3.14)
        self.assertEqual(b2.string, "riverscapes")
        self.assertEqual(b2.lst, [1, 2, 3])
        self.assertEqual(b2.mapping, {"key": "val"})
        self.assertTrue(b2.flag)
        self.assertIsNone(b2.nothing)


# ── Deletion ─────────────────────────────────────────────────────────────────


class TestBorgDeletion(unittest.TestCase):
    def setUp(self):
        Borg._shared_state.clear()

    def tearDown(self):
        Borg._shared_state.clear()

    def test_deletion_on_one_removes_from_other(self):
        """del b1.attr removes the attribute from all instances."""
        b1 = Borg()
        b2 = Borg()
        b1.temp = "remove me"
        self.assertIn("temp", b2.__dict__)
        del b1.temp
        self.assertNotIn("temp", b2.__dict__)

    def test_deletion_removes_from_shared_state(self):
        """Deletion is reflected directly in Borg._shared_state."""
        b = Borg()
        b.ephemeral = True
        del b.ephemeral
        self.assertNotIn("ephemeral", Borg._shared_state)

    def test_other_attributes_survive_deletion(self):
        """Deleting one attribute leaves all other attributes untouched."""
        b1 = Borg()
        b2 = Borg()
        b1.keep = "stays"
        b1.remove = "goes"
        del b1.remove
        self.assertEqual(b2.keep, "stays")
        self.assertFalse(hasattr(b2, "remove"))


# ── State persistence across instantiation ────────────────────────────────────


class TestBorgStatePersistence(unittest.TestCase):
    def setUp(self):
        Borg._shared_state.clear()

    def tearDown(self):
        Borg._shared_state.clear()

    def test_state_visible_to_later_created_instance(self):
        """State written before a second instance exists is visible to that instance."""
        b1 = Borg()
        b1.loaded = True
        b2 = Borg()  # created after the attribute was set
        self.assertTrue(b2.loaded)

    def test_state_survives_original_instance_going_out_of_scope(self):
        """State persists even after the instance that wrote it is garbage-collected."""

        def _write_and_discard():
            b = Borg()
            b.data = "persistent"

        _write_and_discard()  # b is out of scope here
        b_new = Borg()
        self.assertEqual(b_new.data, "persistent")

    def test_state_shared_between_non_overlapping_instances(self):
        """State written by one instance is still there after creating a fresh one."""
        b1 = Borg()
        b1.project = "vbet"
        del b1  # explicitly delete
        b2 = Borg()
        self.assertEqual(b2.project, "vbet")


# ── Guard / initialise-once pattern ──────────────────────────────────────────


class TestBorgGuardPattern(unittest.TestCase):
    """The `if key not in self.__dict__` pattern used by BaseMaps."""

    def setUp(self):
        Borg._shared_state.clear()

    def tearDown(self):
        Borg._shared_state.clear()

    def test_guarded_field_initialised_exactly_once(self):
        """A guarded field is set only on the first __init__ call, not subsequent ones."""

        class _Guarded(Borg):
            def __init__(self):
                Borg.__init__(self)
                if "regions" not in self.__dict__:
                    self.regions = {}  # initialise once

        g1 = _Guarded()
        g1.regions["key"] = "value"
        g2 = _Guarded()  # second init must NOT reset regions to {}
        self.assertEqual(g2.regions, {"key": "value"})

    def test_guard_counter_increments_on_every_init(self):
        """Code *after* the guard runs on every __init__; only the guard itself is skipped."""

        class _Counter(Borg):
            def __init__(self):
                Borg.__init__(self)
                if "count" not in self.__dict__:
                    self.count = 0  # only runs once
                self.count += 1  # runs every time

        c1 = _Counter()
        c2 = _Counter()
        c3 = _Counter()
        # guard fires once (count init'd to 0), then += 1 runs three times → 3
        self.assertEqual(c3.count, 3)

    def test_guard_with_list_field(self):
        """Guard protects a list field from being wiped on re-instantiation."""

        class _Cache(Borg):
            def __init__(self):
                Borg.__init__(self)
                if "items" not in self.__dict__:
                    self.items = []

        c1 = _Cache()
        c1.items.append("first")
        c2 = _Cache()
        self.assertEqual(c2.items, ["first"])


# ── Subclass behaviour ────────────────────────────────────────────────────────


class TestBorgSubclasses(unittest.TestCase):
    """Subclasses that call Borg.__init__ and do not define their own
    _shared_state inherit Borg._shared_state, so they share state with
    the base Borg class and with each other."""

    def setUp(self):
        Borg._shared_state.clear()

    def tearDown(self):
        Borg._shared_state.clear()

    def test_two_subclass_instances_share_state(self):
        """Two instances of the same subclass share state with each other."""
        a1 = _SubA()
        a2 = _SubA()
        a1.result = "shared"
        self.assertEqual(a2.result, "shared")

    def test_subclass_dict_is_borg_shared_state(self):
        """Subclass instance __dict__ is the same object as Borg._shared_state."""
        a = _SubA()
        self.assertIs(a.__dict__, Borg._shared_state)

    def test_subclass_attribute_visible_on_base_borg_instance(self):
        """An attribute set via a subclass instance is visible on a plain Borg instance."""
        a = _SubA()
        a.flag = True
        b = Borg()
        self.assertTrue(b.flag)

    def test_base_borg_attribute_visible_on_subclass_instance(self):
        """An attribute set on a plain Borg instance is visible on subclass instances."""
        b = Borg()
        b.source = "base"
        a = _SubA()
        self.assertEqual(a.source, "base")

    def test_two_different_subclasses_share_state(self):
        """Two distinct subclasses both inherit Borg._shared_state, so they share it.
        This is the expected behaviour of the basic Borg pattern when subclasses
        do not define their own _shared_state."""
        a = _SubA()
        b = _SubB()
        a.shared_value = "cross-class"
        self.assertEqual(b.shared_value, "cross-class")

    def test_subclass_constructor_kwargs_immediately_shared(self):
        """Attributes set during subclass __init__ are immediately in shared state."""
        a1 = _SubA(name="Alice", score=100)
        a2 = _SubA()
        self.assertEqual(a2.name, "Alice")
        self.assertEqual(a2.score, 100)

    def test_subclass_deletion_visible_on_other_subclass(self):
        """Deleting via one subclass instance removes the attribute everywhere."""
        a = _SubA()
        b = _SubB()
        a.temp = "bye"
        del a.temp
        self.assertFalse(hasattr(b, "temp"))


# ── Independent subclass (overrides _shared_state) ───────────────────────────


class TestBorgIsolatedSubclass(unittest.TestCase):
    """A subclass that declares its own _shared_state is fully isolated from
    Borg and from other subclasses."""

    def setUp(self):
        Borg._shared_state.clear()

    def tearDown(self):
        Borg._shared_state.clear()

    def test_isolated_subclass_does_not_share_with_borg(self):
        """A subclass with its own _shared_state is independent of Borg._shared_state."""

        class _Isolated(Borg):
            _shared_state = {}  # own dict — not Borg's

            def __init__(self):
                Borg.__init__(self)

        b = Borg()
        b.base_attr = "base"

        iso = _Isolated()
        self.assertFalse(hasattr(iso, "base_attr"))

    def test_isolated_subclass_instances_share_among_themselves(self):
        """Instances of the isolated subclass still share with *each other*."""

        class _Isolated(Borg):
            _shared_state = {}

            def __init__(self):
                Borg.__init__(self)

        _Isolated._shared_state.clear()
        i1 = _Isolated()
        i2 = _Isolated()
        i1.data = "hello"
        self.assertEqual(i2.data, "hello")

    def test_two_isolated_subclasses_independent(self):
        """Two different subclasses with their own _shared_state don't share."""

        class _IsoX(Borg):
            _shared_state = {}

            def __init__(self):
                Borg.__init__(self)

        class _IsoY(Borg):
            _shared_state = {}

            def __init__(self):
                Borg.__init__(self)

        _IsoX._shared_state.clear()
        _IsoY._shared_state.clear()

        x = _IsoX()
        y = _IsoY()
        x.val = "x-only"
        self.assertFalse(hasattr(y, "val"))


if __name__ == "__main__":
    unittest.main()
