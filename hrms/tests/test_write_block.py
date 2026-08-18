"""Guards the single-writer rule's enforcement (`hrms.sync.write_block`).

During the parallel run exactly one site writes for any given company. Rows
mirrored here carry `synced_from_instance`, and the roadmap's own words are
that violating single-writer "must be blocked in the UI, not just by policy".
These tests pin the block:

* the decision logic (`plan_mirror_write`) is pure and covers every escape
  hatch in precedence order — sync itself, migrate/patch, the per-instance
  cutover unlock, System Manager break-glass;
* the DB stamp always wins over the incoming payload, so a caller cannot
  unlock a row by stripping the stamp from their own request;
* the guard is actually WIRED in hooks.py for every mirrored doctype — and
  `doc_events` has no duplicate doctype keys, because a Python dict literal
  silently drops the earlier entry (this exact bug shipped in the v16 port:
  a second "Employee Checkin" key clobbered the out-of-radius handler);
* the doctype list matches the runner's, so a doctype cannot be mirrored
  but unguarded;
* the checkin sweeper — the one audited `db.set_value` writer that bypasses
  doc events — excludes mirrored rows at the query;
* the cutover switch field exists on HRMS ERP Instance.

Bench-free by construction, like `test_sync_runner.py`. Run as a FILE:

    python3 hrms/tests/test_write_block.py
"""

import ast
import importlib.util
import json
import logging
import pathlib
import sys
import types
import unittest
from typing import ClassVar

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = HRMS_ROOT / "sync" / "write_block.py"
RUNNER_PATH = HRMS_ROOT / "sync" / "runner.py"
HOOKS_PATH = HRMS_ROOT / "hooks.py"
SWEEPER_PATH = HRMS_ROOT / "utils" / "checkin_sweeper.py"
INSTANCE_JSON = HRMS_ROOT / "hr/doctype/hrms_erp_instance/hrms_erp_instance.json"

GUARD = "hrms.sync.write_block.block_mirrored_writes"


def _ensure_stub():
	if "frappe" in sys.modules:
		return
	frappe = types.ModuleType("frappe")
	frappe._ = lambda text: text
	frappe.logger = lambda *a, **kw: logging.getLogger("hrms-test")
	frappe.whitelist = lambda *a, **kw: lambda fn: fn
	frappe.only_for = lambda *a, **kw: None
	frappe.flags = types.SimpleNamespace()
	frappe.db = None
	frappe_utils = types.ModuleType("frappe.utils")
	frappe_utils.now_datetime = lambda: None
	frappe.utils = frappe_utils
	sys.modules["frappe"] = frappe
	sys.modules["frappe.utils"] = frappe_utils


def _load(path, name):
	_ensure_stub()
	spec = importlib.util.spec_from_file_location(name, path)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


wb = _load(MODULE_PATH, "write_block_under_test")


class TestPlanMirrorWrite(unittest.TestCase):
	def _plan(self, stamp, **overrides):
		kwargs = {
			"is_new": False,
			"incoming_stamp": stamp,
			"sync_active": False,
			"maintenance_active": False,
			"unlocked": False,
			"is_system_manager": False,
		}
		kwargs.update(overrides)
		return wb.plan_mirror_write(stamp, **kwargs)

	def test_unstamped_rows_are_untouched(self):
		self.assertEqual(self._plan(None)[0], wb.ALLOW)
		self.assertEqual(self._plan(None, is_new=True, incoming_stamp=None)[0], wb.ALLOW)

	def test_stamped_row_blocks_a_normal_user(self):
		action, reason = self._plan("nasty-live")
		self.assertEqual(action, wb.BLOCK)
		self.assertIn("nasty-live", reason)

	def test_db_stamp_wins_over_the_incoming_payload(self):
		# A caller stripping the stamp from their own request must not unlock
		# the row: the decision reads the DB value, not the payload.
		action, _reason = self._plan("nasty-live", incoming_stamp=None)
		self.assertEqual(action, wb.BLOCK)

	def test_new_row_with_a_forged_stamp_blocks(self):
		# Only the sync inserts stamped rows. A stamped insert from anyone
		# else would corrupt parity counts.
		action, _reason = self._plan(None, is_new=True, incoming_stamp="nasty-live")
		self.assertEqual(action, wb.BLOCK)

	def test_the_sync_itself_is_always_allowed(self):
		self.assertEqual(self._plan("nasty-live", sync_active=True)[0], wb.ALLOW)

	def test_migrate_and_patch_context_is_allowed(self):
		self.assertEqual(self._plan("nasty-live", maintenance_active=True)[0], wb.ALLOW)

	def test_cutover_unlock_allows_plainly(self):
		# The deliberate per-instance switch — not an override, THE mechanism.
		self.assertEqual(self._plan("nasty-live", unlocked=True)[0], wb.ALLOW)

	def test_system_manager_is_break_glass_not_silence(self):
		action, _reason = self._plan("nasty-live", is_system_manager=True)
		self.assertEqual(action, wb.ALLOW_OVERRIDE)

	def test_rename_gets_no_break_glass(self):
		# Renaming a mirrored row guarantees a duplicate on the next pull —
		# corruption, not repair, whoever performs it (SEC-01).
		action, reason = self._plan("nasty-live", is_system_manager=True, is_rename=True)
		self.assertEqual(action, wb.BLOCK)
		self.assertIn("renam", reason.lower())

	def test_rename_is_allowed_once_the_instance_is_unlocked(self):
		# After cutover the sync has stopped; a rename can no longer collide.
		action, _reason = self._plan("nasty-live", unlocked=True, is_rename=True)
		self.assertEqual(action, wb.ALLOW)


class TestStampToPersist(unittest.TestCase):
	def test_existing_rows_always_keep_the_db_value(self):
		# Restores a stripped stamp AND discards a forged one (SEC-03).
		self.assertEqual(wb.stamp_to_persist("nasty-live", None, is_new=False), "nasty-live")
		self.assertIsNone(wb.stamp_to_persist(None, "nasty-live", is_new=False))

	def test_new_rows_keep_their_payload(self):
		# The only stamped inserts that reach this point are the sync's own —
		# a forged stamped insert is BLOCKed before persistence is decided.
		self.assertEqual(wb.stamp_to_persist(None, "nasty-live", is_new=True), "nasty-live")


class TestHooksWiring(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		tree = ast.parse(HOOKS_PATH.read_text(encoding="utf-8"))
		cls.doc_events = next(
			node.value
			for node in ast.walk(tree)
			if isinstance(node, ast.Assign)
			and any(getattr(t, "id", None) == "doc_events" for t in node.targets)
		)

	def _keys(self):
		return [k.value for k in self.doc_events.keys if isinstance(k, ast.Constant)]

	def _strings_under(self, doctype):
		for key, value in zip(self.doc_events.keys, self.doc_events.values, strict=True):
			if isinstance(key, ast.Constant) and key.value == doctype:
				return {
					n.value
					for n in ast.walk(value)
					if isinstance(n, ast.Constant) and isinstance(n.value, str)
				}
		return set()

	def test_doc_events_has_no_duplicate_doctype_keys(self):
		# A duplicate key in a dict literal silently drops the earlier entry —
		# this exact bug disabled the out-of-radius flow in the v16 port.
		keys = self._keys()
		duplicates = sorted({k for k in keys if keys.count(k) > 1})
		self.assertEqual(duplicates, [], f"duplicate doc_events keys silently drop handlers: {duplicates}")

	# Submittable doctypes add the update-after-submit and cancel paths; every
	# doctype needs rename covered, because rename_doc never fires validate.
	REQUIRED_EVENTS: ClassVar[dict[str, tuple[str, ...]]] = {
		"Employee": ("validate", "on_trash", "before_rename"),
		"Employee Checkin": ("validate", "on_trash", "before_rename"),
		"Attendance": (
			"validate",
			"before_update_after_submit",
			"before_cancel",
			"on_trash",
			"before_rename",
		),
		"Leave Ledger Entry": (
			"validate",
			"before_update_after_submit",
			"before_cancel",
			"on_trash",
			"before_rename",
		),
		"Shift Assignment": (
			"validate",
			"before_update_after_submit",
			"before_cancel",
			"on_trash",
			"before_rename",
		),
		# Not submittable: no update-after-submit or cancel path exists to guard.
		"Shift Schedule Assignment": ("validate", "on_trash", "before_rename"),
		# The leave chain — all submittable, so all five paths.
		"Leave Policy Assignment": (
			"validate",
			"before_update_after_submit",
			"before_cancel",
			"on_trash",
			"before_rename",
		),
		"Leave Allocation": (
			"validate",
			"before_update_after_submit",
			"before_cancel",
			"on_trash",
			"before_rename",
		),
		"Leave Application": (
			"validate",
			"before_update_after_submit",
			"before_cancel",
			"on_trash",
			"before_rename",
		),
		"Attendance Request": (
			"validate",
			"before_update_after_submit",
			"before_cancel",
			"on_trash",
			"before_rename",
		),
		"Shift Request": (
			"validate",
			"before_update_after_submit",
			"before_cancel",
			"on_trash",
			"before_rename",
		),
	}

	def _events_carrying_guard(self, doctype):
		for key, value in zip(self.doc_events.keys, self.doc_events.values, strict=True):
			if isinstance(key, ast.Constant) and key.value == doctype and isinstance(value, ast.Dict):
				return {
					event.value
					for event, handlers in zip(value.keys, value.values, strict=True)
					if isinstance(event, ast.Constant)
					and GUARD
					in {
						n.value
						for n in ast.walk(handlers)
						if isinstance(n, ast.Constant) and isinstance(n.value, str)
					}
				}
		return set()

	def test_guard_is_wired_for_every_mirrored_doctype(self):
		for doctype in wb.MIRRORED_DOCTYPES:
			self.assertIn(
				GUARD,
				self._strings_under(doctype),
				f"{doctype} is mirrored but carries no write-block guard in hooks.py",
			)

	def test_every_write_path_carries_the_guard(self):
		self.assertEqual(set(self.REQUIRED_EVENTS), set(wb.MIRRORED_DOCTYPES))
		for doctype, events in self.REQUIRED_EVENTS.items():
			covered = self._events_carrying_guard(doctype)
			missing = [e for e in events if e not in covered]
			self.assertEqual(missing, [], f"{doctype}: guard missing on {missing}")

	#: The transaction guard is a different rule from the row guard: it refuses a
	#: NEW hub-side transaction whose on_submit/on_cancel writes mirrored data for
	#: a mirrored employee, using the EMPLOYEE's provenance rather than the row's.
	#: Every doctype in EMPLOYEE_SCOPED_TRANSACTIONS must carry it on BOTH the
	#: submit and the cancel path — the cascade runs in both directions.
	TRANSACTION_GUARD: ClassVar[str] = "hrms.sync.write_block.block_transactions_for_mirrored_employee"

	def _events_carrying(self, doctype, handler):
		for key, value in zip(self.doc_events.keys, self.doc_events.values, strict=True):
			if isinstance(key, ast.Constant) and key.value == doctype and isinstance(value, ast.Dict):
				return {
					event.value
					for event, handlers in zip(value.keys, value.values, strict=True)
					if isinstance(event, ast.Constant)
					and handler
					in {
						n.value
						for n in ast.walk(handlers)
						if isinstance(n, ast.Constant) and isinstance(n.value, str)
					}
				}
		return set()

	def test_transaction_guard_covers_every_listed_cascade(self):
		"""EMPLOYEE_SCOPED_TRANSACTIONS grew from one entry to the four cascades
		runner.py's own draft-insert comment enumerates. This keeps the list and
		the hooks wiring from drifting apart again — a doctype named in the list
		but unwired is a guard that exists and never fires."""
		self.assertEqual(
			set(wb.EMPLOYEE_SCOPED_TRANSACTIONS),
			{"Leave Application", "Attendance Request", "Shift Request", "Compensatory Leave Request"},
			"EMPLOYEE_SCOPED_TRANSACTIONS changed — update this test AND the hooks wiring together",
		)
		for doctype in wb.EMPLOYEE_SCOPED_TRANSACTIONS:
			covered = self._events_carrying(doctype, self.TRANSACTION_GUARD)
			missing = [e for e in ("before_submit", "before_cancel") if e not in covered]
			self.assertEqual(
				missing,
				[],
				f"{doctype}: transaction guard missing on {missing} — a hub-side "
				f"{doctype} for a mirrored employee would write mirrored data unguarded",
			)

	def test_checkin_keeps_both_after_insert_handlers(self):
		# The two handlers the duplicate key used to clobber must both survive.
		strings = self._strings_under("Employee Checkin")
		self.assertIn("hrms.overrides.employee_checkin_after_insert.create_remote_request_if_needed", strings)
		self.assertIn("hrms.telemetry.on_employee_checkin", strings)


class TestListsStayAligned(unittest.TestCase):
	def test_mirrored_doctypes_match_the_runner(self):
		"""The guard keys off the provenance stamp, so it must cover exactly the
		stamped doctypes.

		Not `DEFAULT_SYNC_DOCTYPES`: that now also lists the create-only masters,
		and those are HR-owned on this hub. Blocking writes to them would lock HR
		out of editing their own Leave Types — a row the guard would refuse for
		carrying a stamp it was never given.
		"""
		runner = _load(RUNNER_PATH, "runner_for_write_block_test")
		self.assertEqual(tuple(wb.MIRRORED_DOCTYPES), tuple(runner.STAMPED_DOCTYPES))
		for master in runner.MASTER_DOCTYPES:
			self.assertNotIn(master, wb.MIRRORED_DOCTYPES)


class TestSetValueWriters(unittest.TestCase):
	def test_checkin_sweeper_excludes_mirrored_rows(self):
		# db.set_value bypasses doc events, so the sweeper cannot be caught by
		# the guard — it must exclude mirrored punches at the query instead.
		self.assertIn(
			"synced_from_instance",
			SWEEPER_PATH.read_text(encoding="utf-8"),
			"checkin_sweeper must filter out mirrored rows before tagging",
		)


class TestCutoverSwitch(unittest.TestCase):
	def test_unlock_field_exists_on_the_instance_doctype(self):
		doc = json.loads(INSTANCE_JSON.read_text(encoding="utf-8"))
		field = next((f for f in doc["fields"] if f.get("fieldname") == "unlock_mirrored_writes"), None)
		self.assertIsNotNone(field, "HRMS ERP Instance needs the unlock_mirrored_writes cutover switch")
		self.assertEqual(field.get("fieldtype"), "Check")
		self.assertIn("unlock_mirrored_writes", doc.get("field_order", []))
		# SEC-02: the cutover switch disables single-writer protection for an
		# entire instance — System-Manager-only, like the credentials beside it.
		self.assertEqual(field.get("permlevel"), 1, "cutover switch must be permlevel 1")


if __name__ == "__main__":
	unittest.main()
