"""The status a list shows must be the status that decides anything.

Nabil, 10 September, reading the Shift Assignment list: "the status shown
submitted. but for how long? isnt it suppose not show these? if they are
approve then approved?"

He was right, and it cost us an afternoon. Every submittable doctype carries a
DOCUMENT state — Draft / Submitted / Cancelled — which Frappe renders as the
list's status indicator. Several of these doctypes ALSO carry a `status` field
that means something entirely different and is the one the code reads:

    Shift Assignment    Active / Inactive        <- the shift resolver reads this
    Shift Request       Draft / Approved / Rejected
    Leave Application   Open / Approved / Rejected / Cancelled

None of those three were in their list view. So the list answered "is this
record filed?" while looking like it answered "is this in force?" — and while
diagnosing the Tampin night-shift bug we could not tell from the list whether
an employee's assignment was live. `created_by_shift_rule` was worse: hidden
outright, so there was no way to see which assignments the system had made for
itself.

JSON only — no bench required.
"""

import json
import pathlib
import unittest

HRMS = pathlib.Path(__file__).resolve().parent.parent

# doctype path -> the field whose value decides what the record DOES
DECIDING_STATUS = {
	"hr/doctype/shift_assignment/shift_assignment.json": "status",
	"hr/doctype/shift_request/shift_request.json": "status",
	"hr/doctype/leave_application/leave_application.json": "status",
	"hr/doctype/attendance_request/attendance_request.json": "status",
	"hr/doctype/ot_request/ot_request.json": "status",
}


def _fields(rel: str) -> dict:
	doc = json.loads((HRMS / rel).read_text())
	return {f["fieldname"]: f for f in doc["fields"]}


class TestTheDecidingStatusIsOnScreen(unittest.TestCase):
	def test_every_deciding_status_is_a_list_column(self):
		for rel, fieldname in DECIDING_STATUS.items():
			field = _fields(rel).get(fieldname)
			self.assertIsNotNone(field, f"{rel} has no {fieldname} field")
			self.assertTrue(
				field.get("in_list_view"),
				f"{rel}: `{fieldname}` decides what this record does, but the list shows only "
				f"the document state (Draft/Submitted/Cancelled). The page looks like it "
				f"answers 'is this in force?' and actually answers 'is this filed?'",
			)

	def test_a_deciding_status_is_never_hidden(self):
		for rel, fieldname in DECIDING_STATUS.items():
			field = _fields(rel)[fieldname]
			self.assertFalse(field.get("hidden"), f"{rel}: `{fieldname}` is hidden")

	def test_an_assignment_says_whether_the_system_made_it(self):
		"""Two things create Shift Assignments: a person, and the daily shift-rule
		sync. They are governed by different rules — the sync closes and replaces
		its own rows and stands off anyone else's — so 'who made this' is the
		first question when an assignment behaves unexpectedly. It was hidden."""
		field = _fields("hr/doctype/shift_assignment/shift_assignment.json")["created_by_shift_rule"]
		self.assertFalse(
			field.get("hidden"),
			"created_by_shift_rule is hidden, so nobody can tell a rule-made assignment "
			"from a hand-made one — which is exactly what the shift-rule layer branches on",
		)
		self.assertTrue(field.get("read_only"), "it is a system marker; nobody should type it")


if __name__ == "__main__":
	unittest.main()
