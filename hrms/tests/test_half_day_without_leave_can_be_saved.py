"""A Half Day earned by short hours must not demand a Leave Type.

Reported 17 Sep 2026. HR opened Norazlin's 4 September Attendance in Desk to
correct it and could not save ANYTHING: "Please fill the following mandatory
fields before saving: Leave Type is required." The row is a Half Day the
hourly job produced from working hours — there is no leave, and there is no
Leave Type to name.

Two rules in this doctype disagree:

* `Attendance.check_leave_record` (attendance.py) explicitly supports a Half
  Day with NO leave: when it finds no Leave Application for the date it sets
  `half_day_status = "Absent"` and only raises an alert. That is how every
  hours-based Half Day in this app is written.
* the `leave_type` field carried
  `mandatory_depends_on: eval:in_list(["On Leave", "Half Day"], doc.status)`
  — upstream's assumption that a Half Day is always half a day of LEAVE.

The automation writes the row anyway; a person opening it cannot. So the only
rows HR ever needs to correct are exactly the rows HR cannot save, and the
whole Desk correction path is shut for them.

`leave_type` stays mandatory for On Leave, and stays VISIBLE on a Half Day so
HR can still name the type when the half day really is leave — and when it is,
`check_leave_record` fills it from the approved Leave Application by itself.

    PYTHONPATH=. python3 -m pytest -q \
        hrms/tests/test_half_day_without_leave_can_be_saved.py
"""

from __future__ import annotations

import ast
import json
import pathlib
import unittest

HRMS = pathlib.Path(__file__).resolve().parents[1]
ATTENDANCE = HRMS / "hr" / "doctype" / "attendance"


def field(fieldname: str) -> dict:
	meta = json.loads((ATTENDANCE / "attendance.json").read_text())
	return next(f for f in meta["fields"] if f.get("fieldname") == fieldname)


class LeaveTypeMandatoryCase(unittest.TestCase):
	def test_a_half_day_does_not_demand_a_leave_type(self):
		rule = field("leave_type").get("mandatory_depends_on") or ""
		self.assertNotIn(
			"Half Day",
			rule,
			"an hours-based Half Day has no leave and no Leave Type to name — "
			"HR could not save the very rows they opened to correct",
		)

	def test_on_leave_still_demands_one(self):
		rule = field("leave_type").get("mandatory_depends_on") or ""
		self.assertIn("On Leave", rule, "a day OFF on leave must still name the leave type")

	def test_the_field_is_still_offered_on_a_half_day(self):
		"""A half day CAN be leave; HR must still be able to name it."""
		shown = field("leave_type").get("depends_on") or ""
		self.assertIn("Half Day", shown)
		self.assertIn("On Leave", shown)


class ControllerAgreesCase(unittest.TestCase):
	"""The controller is the reason the mandatory rule was wrong, not the JSON."""

	def test_check_leave_record_accepts_a_half_day_with_no_leave(self):
		source = (ATTENDANCE / "attendance.py").read_text()
		tree = ast.parse(source)
		fn = next(
			node
			for node in ast.walk(tree)
			if isinstance(node, ast.FunctionDef) and node.name == "check_leave_record"
		)
		body = ast.unparse(fn)
		self.assertIn(
			"self.half_day_status = 'Absent'",
			body,
			"check_leave_record must keep treating a leave-less Half Day as a real state",
		)


if __name__ == "__main__":
	unittest.main()
