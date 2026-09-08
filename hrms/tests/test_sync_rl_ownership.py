"""A source pull keeps the Replacement Leave days the hub granted on a mirrored allocation.

DS4 (8 Sep 2026 Desk/sync audit): approving an OT Request for Replacement
Leave tops up the employee's Leave Allocation — a MIRRORED row when the
employee comes from a source instance. The sync's update path overwrote the
allocation's totals with the source's values, and the old advice ("release
the mirror stamp before a re-pull") was disproven: an unstamped row is
exactly what the first writer may claim. A 3-day allocation (2 from the
source + 1 granted on the hub) went back to 2 on the next pull.

Ownership is now explicit and enforceable: the source owns its balance, the
hub owns its grants, and the two are kept apart on the ledger. Hub grants
are the Leave Ledger Entries the source never held — unstamped, submitted,
transaction Leave Allocation — and a source update lands as source total
plus hub grants, so neither side loses what it wrote.

Bench-free on the sync runner harness (hrms/tests/test_sync_runner.py).
    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_sync_rl_ownership.py
"""

import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
harness = importlib.import_module("test_sync_runner")
runner = harness.runner
_HARNESS_MATCHES = harness._matches
#: The `frappe` the runner bound at import. Several standalone test modules
#: replace sys.modules["frappe"] with a bare module at THEIR import (a shared
#: pytest session collects every file before running any), and the harness's
#: setUp patches whatever `import frappe` resolves to — so it must resolve to
#: the runner's own module, or the store never reaches the code under test.
_RUNNER_FRAPPE = runner.frappe
SOURCE = "nasty-live"
ALLOCATION = "HR-LAL-2026-0007"


def _matches(row, filters):
	"""The harness matcher plus the `("is", "set"|"not set")` operator."""
	for field, condition in (filters or {}).items():
		value = row.get(field)
		if isinstance(condition, tuple | list) and condition[0] == "is":
			if (value is None or value == "") != (condition[1] == "not set"):
				return False
			continue
		if not _HARNESS_MATCHES({field: value}, {field: condition}):
			return False
	return True


def ledger(name, allocation, leaves, stamp=None, **extra):
	row = dict(
		name=name,
		transaction_type="Leave Allocation",
		transaction_name=allocation,
		leaves=leaves,
		docstatus=1,
		is_carry_forward=0,
		is_expired=0,
		synced_from_instance=stamp,
	)
	row.update(extra)
	return row


class TestHubGrantsSurviveASourcePull(harness._RunnerTestCase):
	SEED_EXCLUDE = ("Leave Allocation",)

	def setUp(self):
		previous = sys.modules.get("frappe")
		sys.modules["frappe"] = _RUNNER_FRAPPE
		self.addCleanup(sys.modules.__setitem__, "frappe", previous)
		super().setUp()
		patcher = patch.object(harness, "_matches", _matches)
		patcher.start()
		self.addCleanup(patcher.stop)
		# this site's Leave Allocation stores both totals, as the real one does
		columns = set(harness.FAKE_LEAVE_ALLOCATION_COLUMNS) | {"total_leaves_allocated"}
		schema = patch.object(runner, "_local_schema", lambda doctype: (columns, {}))
		schema.start()
		self.addCleanup(schema.stop)
		self.seed_parent(
			"Leave Allocation",
			ALLOCATION,
			employee="HR-EMP-0001",
			leave_type="Replacement Leave",
			new_leaves_allocated=3,
			total_leaves_allocated=3,
			docstatus=1,
			synced_from_instance=SOURCE,
		)
		self.store.tables["Leave Ledger Entry"] = {
			"LLE-SRC": ledger("LLE-SRC", ALLOCATION, 2, stamp=SOURCE),  # the source's own allocation
			"LLE-HUB": ledger("LLE-HUB", ALLOCATION, 1),  # granted on the hub (OT -> RL)
		}

	def pull(self, new_leaves):
		runner._write_row.dropped_fields = {}
		return runner._write_row(
			"Leave Allocation",
			ALLOCATION,
			{
				"employee": "HR-EMP-0001",
				"leave_type": "Replacement Leave",
				"new_leaves_allocated": new_leaves,
				"total_leaves_allocated": new_leaves,
				"docstatus": 1,
				"synced_from_instance": SOURCE,
			},
		)

	def row(self):
		return self.store.rows("Leave Allocation")[ALLOCATION]

	def test_the_hub_granted_day_rides_on_top_of_the_source_total(self):
		self.assertEqual(self.pull(2), "updated")
		self.assertEqual((self.row()["new_leaves_allocated"], self.row()["total_leaves_allocated"]), (3, 3))
		self.assertEqual(self.row()["synced_from_instance"], SOURCE, "the row stays the source's")

	def test_a_raised_source_balance_and_the_hub_grant_are_both_kept(self):
		self.pull(5)
		self.assertEqual(self.row()["total_leaves_allocated"], 6)

	def test_mirrored_ledger_entries_are_not_hub_grants(self):
		self.store.tables["Leave Ledger Entry"].pop("LLE-HUB")
		self.pull(2)
		self.assertEqual(
			self.row()["total_leaves_allocated"], 2, "no hub grant: the source value lands as is"
		)

	def test_cancelled_or_expired_hub_entries_do_not_count(self):
		self.store.tables["Leave Ledger Entry"]["LLE-HUB"]["docstatus"] = 2
		self.store.tables["Leave Ledger Entry"]["LLE-OLD"] = ledger("LLE-OLD", ALLOCATION, 4, is_expired=1)
		self.pull(2)
		self.assertEqual(self.row()["total_leaves_allocated"], 2)


if __name__ == "__main__":
	unittest.main()
