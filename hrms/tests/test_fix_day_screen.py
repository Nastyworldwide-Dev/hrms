"""The Fix Day screen and the three doors into it.

Static checks over the shipped sources — no bench, no browser:

* the screen offers the five evidence actions and the undo, and NOTHING that
  types an hour, an overtime figure or a status (the owner rule the whole
  feature exists to keep);
* every server call it makes is a whitelisted POST endpoint of
  hrms.api.attendance_fix_day, and every endpoint of that module is POST-only
  (a GET would let a link change attendance);
* the Unclaimable Days report, the Shift Attendance report and the Employee
  Checkin list each open the screen, and each is HR-gated.

    PYTHONPATH=. python3 hrms/tests/test_fix_day_screen.py
"""

import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "public/js/fix_day.bundle.js"
API = ROOT / "api/attendance_fix_day.py"
UNCLAIMABLE = ROOT / "hr/report/unclaimable_days/unclaimable_days.js"
SHIFT_ATTENDANCE = ROOT / "hr/report/shift_attendance/shift_attendance.js"

# Six since 17 Sep 2026: HR can take a day back to ONE attendance row from the
# same screen, instead of a two-row day being untouchable everywhere.
ACTIONS = ("pair_taps", "move_tap", "ignore_tap", "restore_tap", "add_tap", "remove_duplicate_row")
#: what a control on this screen must never be for
RESULT_WORDS = ("working_hours", "ot_hours", "overtime_hours", "hours_worked")


def read(path):
	return path.read_text(encoding="utf-8")


class TestTheScreenOffersEvidenceOnly(unittest.TestCase):
	def setUp(self):
		self.js = read(BUNDLE)

	def test_the_five_actions_and_the_undo_are_all_it_can_do(self):
		read = set(re.findall(r'FD_API \+ "(\w+)"', self.js))
		writes = set(re.findall(r'this\.run\("(\w+)"', self.js))
		self.assertEqual(read, {"get_day"}, "the only direct call is the read")
		self.assertEqual(writes, {"undo_fix", *ACTIONS})
		# every write goes through the one `run`, which reloads and shows before/after
		self.assertIn("fd_call(FD_API + method, args)", self.js)

	def test_no_control_edits_a_result(self):
		fields = re.findall(r'fieldname: "(\w+)"', self.js)
		for field in fields:
			self.assertNotIn("hour", field.lower(), f"{field} would let HR type a result")
			self.assertNotIn("ot_", field.lower(), f"{field} would let HR type a result")
		for word in RESULT_WORDS:
			self.assertNotIn(f'fieldname: "{word}"', self.js)
		# no status control either: the engine decides the status from the taps
		self.assertNotIn('fieldname: "status"', self.js)

	def test_it_says_out_loud_that_hours_are_not_typed(self):
		self.assertIn("never typed here", self.js)

	def test_only_hr_opens_it(self):
		self.assertIn('FD_HR_ROLES = ["HR User", "HR Manager", "System Manager"]', self.js)
		self.assertIn("if (!fd_enabled())", self.js)

	def test_every_action_states_a_reason(self):
		"""`ask` adds a required Reason to every action dialog, so no correction
		lands without one on the tap and in the fix log."""
		self.assertIn('fieldname: "reason", label: __("Reason"), fieldtype: "Small Text", reqd: 1', self.js)


class TestTheEndpointsArePostOnly(unittest.TestCase):
	def setUp(self):
		self.source = read(API)

	def test_every_whitelisted_endpoint_is_post_only(self):
		decorated = re.findall(r"@frappe\.whitelist\(([^)]*)\)\ndef (\w+)", self.source)
		self.assertTrue(decorated, "expected whitelisted endpoints")
		for args, name in decorated:
			self.assertIn('methods=["POST"]', args, f"{name} must be POST only")

	def test_the_endpoints_are_exactly_the_six_actions_the_read_and_the_undo(self):
		names = {name for _, name in re.findall(r"@frappe\.whitelist\(([^)]*)\)\ndef (\w+)", self.source)}
		self.assertEqual(names, {"get_day", "undo_fix", *ACTIONS})

	def test_every_endpoint_checks_the_role_first(self):
		for name in ("get_day", "undo_fix", *ACTIONS):
			body = self.source.split(f"def {name}(", 1)[1].split("\n\n\n", 1)[0]
			self.assertIn("_require_hr()", body, f"{name} does not check the role")

	def test_the_company_fence_is_applied_to_the_employee(self):
		self.assertIn("company_scope.company_visible", self.source)


class TestTheFixLogIsSharedWithTheBackfills(unittest.TestCase):
	"""One log for every writer that changes an employee-day.

	Part B's ERP backfill needs the same record (before/after per employee-day,
	undo for one day, one employee or a whole run). A second log doctype would
	mean two shapes, two undos and two places to read a day's history — so the
	shape here is deliberately writer-agnostic and pinned by these tests.
	"""

	def setUp(self):
		self.spec = json.loads((ROOT / "hr/doctype/hr_day_fix_log/hr_day_fix_log.json").read_text())
		self.fields = {f["fieldname"]: f for f in self.spec["fields"] if f.get("fieldname")}

	def test_it_carries_the_generic_record_every_writer_needs(self):
		for fieldname in (
			"source",
			"run",
			"employee",
			"fix_date",
			"action",
			"refs",
			"reason",
			"fixed_by",
			"before_state",
			"after_state",
			"undone",
			"undone_by",
			"undone_on",
			"undo_of",
		):
			self.assertIn(fieldname, self.fields)

	def test_action_is_free_text_so_a_second_writer_needs_no_schema_change(self):
		self.assertEqual(self.fields["action"]["fieldtype"], "Data")

	def test_source_names_every_writer_of_this_log(self):
		options = set(self.fields["source"]["options"].split("\n"))
		self.assertEqual(options, {"hr_fix_day", "erp_backfill", "recovery"})
		self.assertEqual(self.fields["source"]["reqd"], 1)

	def test_a_batch_can_be_undone_as_one_run(self):
		self.assertEqual(self.fields["run"]["fieldtype"], "Data")

	def test_the_before_and_after_are_free_json(self):
		for fieldname in ("before_state", "after_state"):
			self.assertEqual(self.fields[fieldname]["fieldtype"], "Code")
			self.assertEqual(self.fields[fieldname]["options"], "JSON")

	def test_no_field_is_writable_by_hand(self):
		for fieldname, field in self.fields.items():
			if field["fieldtype"] in ("Section Break", "Column Break"):
				continue
			self.assertEqual(field.get("read_only"), 1, f"{fieldname} must be read-only")

	def test_field_order_and_fields_agree(self):
		ordered = [f for f in self.spec["field_order"]]
		self.assertEqual(ordered, [f["fieldname"] for f in self.spec["fields"]])


class TestTheThreeDoors(unittest.TestCase):
	def test_unclaimable_days_opens_it_for_the_ticked_row(self):
		js = read(UNCLAIMABLE)
		self.assertIn('frappe.require("fix_day.bundle.js"', js)
		self.assertIn("hrms.fix_day.open(", js)
		self.assertIn('add_inner_button(__("Fix")', js)
		self.assertIn("UD_HR_ROLES", js)

	def test_shift_attendance_opens_it_for_one_ticked_day(self):
		js = read(SHIFT_ATTENDANCE)
		self.assertIn('frappe.require("fix_day.bundle.js"', js)
		self.assertIn("hrms.fix_day.open(", js)
		self.assertIn('add_inner_button(__("Fix day")', js)
		# the master edit's own HR gate already wraps setup_toolbar
		self.assertIn("if (sa_enabled()) sa_grid(report).setup_toolbar();", js)

	def test_the_employee_checkin_list_opens_it_for_one_employee_day(self):
		js = read(BUNDLE)
		self.assertIn('frappe.listview_settings["Employee Checkin"]', js)
		self.assertIn("hrms.fix_day.from_taps", js)
		self.assertIn("Tick taps of one person on one day.", js)


if __name__ == "__main__":
	unittest.main()
