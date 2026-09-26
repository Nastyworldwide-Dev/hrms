"""The Fix Day screen and the three doors into it.

Static checks over the shipped sources — no bench, no browser:

* the screen offers the five evidence actions and the undo, and NOTHING that
  types an hour, an overtime figure or a status (the owner rule the whole
  feature exists to keep);
* every server call it makes is a whitelisted POST endpoint of
  hrms.api.attendance_fix_day, and every endpoint of that module is POST-only
  (a GET would let a link change attendance);
* the Employee Checkin list is the ONLY door (owner, 21 Sep 2026); the
  Unclaimable Days report, the Shift Attendance report and the Attendance list
  link there with "Punches" and open nothing themselves.

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
# same screen, instead of a two-row day being untouchable everywhere. Seven the
# same evening: the owner did one day through five dialogs and five typed
# reasons and asked for one step, so `rebuild_day` applies the whole plan at
# once. The five single actions stay for the days the plan refuses.
# Eight since 18 Sep 2026: a punch the old ERP sent is refused by this screen and
# invisible to the hourly job, so any day whose closing punch came from there was
# unfixable. `claim_tap` takes one over, after cutover only.
ACTIONS = (
	"rebuild_day",
	"claim_tap",
	"pair_taps",
	"move_tap",
	"ignore_tap",
	"restore_tap",
	"add_tap",
	"remove_duplicate_row",
)
#: Nine since 21 Sep 2026: a date range in one press (the loop is
#: attendance_fix_days). An endpoint on this module; its Desk dialog is the next
#: slice, so the bundle's write set does not carry it yet.
#: `save_day` (21 Sep 2026, one "Fix attendance" button) is the same shape: the
#: endpoint lands first, the dialog's Save & rebuild is slice B.
RANGE_ACTIONS = ("fix_days", "save_day")
#: reads: `get_day` paints the screen, `plan_day` says what the rebuild would do
READS = ("get_day", "plan_day")
#: what a control on this screen must never be for
RESULT_WORDS = ("working_hours", "ot_hours", "overtime_hours", "hours_worked")


def read(path):
	return path.read_text(encoding="utf-8")


class TestTheScreenOffersEvidenceOnly(unittest.TestCase):
	def setUp(self):
		self.js = read(BUNDLE)

	def test_the_screen_reads_one_way_and_writes_one_way(self):
		"""Amended 21 Sep 2026 (one "Fix attendance" button): the dialog reads the
		day with `get_day`, writes it with `save_day` (HR's ticked pair is the
		evidence; the engine recomputes the row) and undoes with `undo_fix`.
		The eight single actions stay on the module for history and undo, but no
		button on the screen reaches them any more.

		Amended 22 Sep 2026: `move_tap` is the ninth, and it is here on purpose.
		A day carrying two Attendance rows refuses every rebuild (day_block_reason)
		and `duplicate_refusal` answers "Move a tap to the row it belongs to
		first" — a sentence that was only true while a door existed. It is the one
		action the server allows on a two-row day (duplicate_rows_ok=True) because
		it is the way OUT of one. It re-stamps ONE punch; a DAY is still written
		one way only, by save_day from HR's ticks."""
		calls = set(re.findall(r'FD_API \+ "(\w+)"', self.js))
		self.assertEqual(calls, {"get_day", "save_day", "undo_fix", "move_tap"})
		self.assertEqual(len(re.findall(r'FD_API \+ "save_day"', self.js)), 1, "one way to write a day")
		# move_tap is back on the screen (see the docstring); the other seven
		# stay endpoints only.
		for action in ACTIONS:
			if action == "move_tap":
				continue
			self.assertNotIn(f'"{action}"', self.js, f"{action} is no longer a button")
		self.assertNotIn("fix_days", self.js, "the range form is retired")

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
		reason = re.search(
			r'fieldname: "reason",\s*label: __\("Reason"\),\s*fieldtype: "Small Text",\s*reqd: 1', self.js
		)
		self.assertIsNotNone(reason, "Save & rebuild needs a reason")


class TestTheEndpointsArePostOnly(unittest.TestCase):
	def setUp(self):
		self.source = read(API)

	def test_every_whitelisted_endpoint_is_post_only(self):
		decorated = re.findall(r"@frappe\.whitelist\(([^)]*)\)\ndef (\w+)", self.source)
		self.assertTrue(decorated, "expected whitelisted endpoints")
		for args, name in decorated:
			self.assertIn('methods=["POST"]', args, f"{name} must be POST only")

	def test_the_endpoints_are_exactly_the_actions_the_reads_and_the_undo(self):
		names = {name for _, name in re.findall(r"@frappe\.whitelist\(([^)]*)\)\ndef (\w+)", self.source)}
		self.assertEqual(names, {*READS, "undo_fix", *ACTIONS, *RANGE_ACTIONS})

	def test_every_endpoint_checks_the_role_first(self):
		for name in (*READS, "undo_fix", *ACTIONS, *RANGE_ACTIONS):
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
		self.assertEqual(options, {"hr_fix_day", "erp_backfill", "recovery", "day_remark"})
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


class TestTheOneDoor(unittest.TestCase):
	"""Amended 21 Sep 2026: the owner moved the tool to the punches page. The
	reports and the Attendance list LINK there ("Punches" -> the Employee
	Checkin list on that employee-day) and open nothing themselves."""

	PUNCHES = 'frappe.set_route("List", "Employee Checkin"'

	def test_unclaimable_days_links_to_the_punches_and_opens_nothing(self):
		js = read(UNCLAIMABLE)
		self.assertNotIn("fix_day.bundle.js", js)
		self.assertNotIn("hrms.fix_day", js)
		self.assertIn('add_inner_button(__("Punches")', js)
		self.assertIn(self.PUNCHES, js)
		self.assertIn("UD_HR_ROLES", js)

	def test_shift_attendance_links_to_the_punches_and_opens_nothing(self):
		js = read(SHIFT_ATTENDANCE)
		self.assertNotIn("fix_day.bundle.js", js)
		self.assertNotIn("hrms.fix_day", js)
		self.assertIn('add_inner_button(__("Punches")', js)
		self.assertIn(self.PUNCHES, js)
		# the master edit's own HR gate already wraps setup_toolbar
		self.assertIn("if (sa_enabled()) sa_grid(report).setup_toolbar();", js)

	def test_missed_checkouts_links_to_the_punches_and_opens_nothing(self):
		# alpha.11: the report suggests a check-out; HR confirms it on the one door.
		js = read(ROOT / "hr/report/missed_checkouts_after_midnight/missed_checkouts_after_midnight.js")
		self.assertNotIn("fix_day.bundle.js", js)
		self.assertNotIn("hrms.fix_day", js)
		self.assertIn('add_inner_button(__("Punches")', js)
		self.assertIn(self.PUNCHES, js)
		self.assertIn("MC_HR_ROLES", js)

	def test_the_attendance_list_links_to_the_punches_and_opens_nothing(self):
		self.assertNotIn("hrms.fix_day.from_attendance", read(BUNDLE))
		listing = read(ROOT / "hr/doctype/attendance/attendance_list.js")
		self.assertNotIn("hrms.fix_day", listing)
		self.assertIn('add_inner_button(__("Punches")', listing)
		self.assertIn(self.PUNCHES, listing)

	def test_the_employee_checkin_list_opens_it_for_one_employee_day(self):
		"""Amended 17 Sep 2026 (cba7c3f11). The bundle used to assign
		`frappe.listview_settings["Employee Checkin"]` itself, at boot, and the
		doctype's own list script — loaded when the list opens — threw it away,
		so HR never saw the button. The bundle keeps the opener; the list script
		is the door."""
		js = read(BUNDLE)
		self.assertNotIn(
			'frappe.listview_settings["Employee Checkin"] =',
			js,
			"a boot bundle cannot own that key; the list script is loaded last",
		)
		self.assertIn("hrms.fix_day.from_taps", js)
		# Amended 18 Sep 2026: a shift that runs past midnight puts ONE session on
		# two calendar dates, and refusing that refused the commonest broken day
		# here. Two PEOPLE is still refused; the opener works out which day.
		self.assertIn("Tick taps of one person.", js)
		listing = read(ROOT / "hr/doctype/employee_checkin/employee_checkin_list.js")
		self.assertIn("hrms.fix_day.from_taps(listview)", listing)

	def test_the_employee_checkin_list_has_exactly_one_fix_button(self):
		"""21 Sep 2026: "Fix day" and "Fix days" confused HR (same name, one
		letter apart). One button, one dialog: tick the pair, Save & rebuild."""
		js = read(BUNDLE)
		self.assertNotIn("fix_days_from_taps", js)
		self.assertNotIn("class FixDaysDialog", js)
		self.assertIn("Save & rebuild", js)
		listing = read(ROOT / "hr/doctype/employee_checkin/employee_checkin_list.js")
		self.assertEqual(listing.count("add_inner_button"), 1)
		self.assertIn('add_inner_button(__("Fix attendance")', listing)
		self.assertNotIn('__("Fix day")', listing)
		self.assertNotIn('__("Fix days")', listing)


if __name__ == "__main__":
	unittest.main()
