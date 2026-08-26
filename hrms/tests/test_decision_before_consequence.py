"""Three request types could be approved but never declined — and the fix is a trap.

An approver could press Submit on an OT Request, an Attendance Request or a
Replacement Leave Claim, and had no way at all to REJECT one. The PWA's
Approve/Reject pair renders only when `doc.status` is `Open` or `Draft`, and
none of the three had a `status` field, so the block never appeared. The only
options were to leave a draft sitting for ever or delete it in Desk — and
deleting runs against the standing rule that nothing is removed, only parked.

Giving them a `status` field is the obvious fix and it is dangerous, because all
three DO something on submit:

    OT Request                banks replacement-leave hours
    Attendance Request        creates Attendance records
    Replacement Leave Claim   adds days to a Leave Allocation

A rejected request still reaches docstatus 1 — rejection is a decision, not a
cancellation — so without a guard, declining one would pay it out anyway.
Rejected overtime would grant leave; a refused attendance request would mark
attendance.

`ShiftRequest.on_submit` already solves this and is the pattern followed here:
refuse an undecided document, then perform the consequence ONLY when the
decision was Approved.

The OT bank query is the sharpest case and has its own test below: it selects on
`docstatus: 1` alone, so a rejected row would have been counted as banked hours
without anybody touching `on_submit`.

Bench-free: read from the AST and the doctype JSON. Run it as a FILE:

    python3 hrms/tests/test_decision_before_consequence.py
"""

import ast
import json
import pathlib
import unittest

HR = pathlib.Path(__file__).resolve().parents[1] / "hr/doctype"

#: doctype dir -> the method whose effect must not run on a rejection
CONSEQUENCE = {
	"ot_request": None,  # no method; the BANK QUERY is the effect. See its own test.
	"attendance_request": "create_attendance_records",
	"replacement_leave_claim": "add_to_leave_allocation",
}


def meta(name):
	return json.loads((HR / name / f"{name}.json").read_text())


def field(name, fieldname):
	return next((f for f in meta(name)["fields"] if f["fieldname"] == fieldname), None)


def fn(name, func):
	tree = ast.parse((HR / name / f"{name}.py").read_text())
	return next(
		(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == func),
		None,
	)


class TestEachOneCanBeDeclined(unittest.TestCase):
	"""Without a status field the PWA cannot render Reject at all."""

	def test_they_have_a_status_field(self):
		for name in CONSEQUENCE:
			with self.subTest(name):
				f = field(name, "status")
				self.assertIsNotNone(f, f"{name} has no status field, so it cannot be declined")
				self.assertEqual(f["fieldtype"], "Select")

	def test_the_options_are_the_ones_the_ui_looks_for(self):
		"""RequestActionSheet renders Approve/Reject on `Open`/`Draft`, and
		`hrms.api.approval.DECISIONS` writes only Approved/Rejected. A different
		vocabulary here means the buttons never appear."""
		for name in CONSEQUENCE:
			with self.subTest(name):
				options = [o.strip() for o in field(name, "status")["options"].split("\n") if o.strip()]
				self.assertEqual(options, ["Open", "Approved", "Rejected"])

	def test_the_decision_is_displayed_never_typed(self):
		"""read_only=1 on all three. The visual gate caught the status Select
		rendering as the FIRST control on an employee's New OT Request — a
		decision offered to the person who does not make it. Leave Application
		hides its status behind permlevel 1; these three have no level-1 perm
		rows, so read_only is the enforcement that fits: decide() writes the
		field server-side, nobody types it."""
		for name in CONSEQUENCE:
			with self.subTest(name):
				self.assertEqual(field(name, "status").get("read_only"), 1)

	def test_status_defaults_to_open(self):
		"""A blank status renders no buttons — the same dead end, one step later."""
		for name in CONSEQUENCE:
			with self.subTest(name):
				self.assertEqual(field(name, "status").get("default"), "Open")


class TestAnUndecidedRequestCannotBeSubmitted(unittest.TestCase):
	"""Submitting IS the payout. It must not happen before somebody decided."""

	def test_on_submit_refuses_a_status_that_is_not_a_decision(self):
		for name in CONSEQUENCE:
			with self.subTest(name):
				src = ast.unparse(fn(name, "on_submit"))
				self.assertIn("Approved", src)
				self.assertIn("Rejected", src)


class TestARejectionNeverPaysOut(unittest.TestCase):
	"""The trap this whole file exists for.

	A rejected request still reaches docstatus 1 — rejection is a decision, not
	a cancellation. So every consequence must be guarded on the decision, or
	declining a request performs it anyway."""

	def test_the_consequence_runs_only_when_approved(self):
		for name, method in CONSEQUENCE.items():
			if not method:
				continue
			with self.subTest(name):
				src = ast.unparse(fn(name, "on_submit"))
				self.assertIn(method, src, f"{name}.on_submit no longer calls {method}")
				guard = src.index("== 'Approved'") if "== 'Approved'" in src else -1
				self.assertGreater(guard, -1, f"{name}.on_submit does not test for Approved before acting")
				self.assertGreater(
					src.index(method),
					guard,
					f"{name} performs {method} before checking the decision",
				)

	def test_the_ot_bank_excludes_rejected_hours(self):
		"""The sharpest case, and the one with no on_submit to guard.

		`get_replacement_leave_bank` selects OT Requests on `docstatus: 1` alone.
		A rejected row reaches docstatus 1, so without this filter declining
		overtime would still bank the hours and grant replacement leave — money,
		out of a button that says Reject."""
		src = ast.unparse(fn("ot_request", "get_replacement_leave_bank"))
		self.assertIn("status", src, "the bank query does not look at status at all")
		self.assertIn(
			"Rejected",
			src,
			"the bank query counts rejected overtime as banked hours",
		)


class TestTheServerKnowsTheyAreDecidable(unittest.TestCase):
	def test_they_are_registered_for_decide_then_submit(self):
		"""`hrms.api.approval` is the authority; RequestActionSheet holds a copy
		that only chooses which call to make. Absent here, a decision would fall
		back to the plain-transition path and the status would never be written."""
		api = pathlib.Path(__file__).resolve().parents[1] / "api/approval.py"
		tree = ast.parse(api.read_text())
		mapping = next(
			n
			for n in ast.walk(tree)
			if isinstance(n, ast.Assign)
			and any(getattr(t, "id", "") == "DECIDE_THEN_SUBMIT" for t in n.targets)
		)
		registered = {k.value for k in mapping.value.keys}
		for doctype in ("OT Request", "Attendance Request", "Replacement Leave Claim"):
			self.assertIn(doctype, registered)


if __name__ == "__main__":
	unittest.main()
