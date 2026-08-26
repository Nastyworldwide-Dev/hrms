"""Approve and Cancel in the PWA did nothing at all, and said so only in a toast.

REPORTED FROM THE FIELD: an employee's OT Request was approved, and the app went
on asking him to submit it. Reproduced against a real database in one line:

    set_value REFUSED -> ValidationError Cannot edit standard fields
    docstatus still: 0

`RequestActionSheet.updateDocumentStatus` sends `{docstatus: 1}` through
frappe-ui's `document.setValue`, which is `frappe.client.set_value` — and that
refuses to write `docstatus`, because docstatus is a standard field and moving
it is a TRANSITION, not an edit. Submitting has to run validate, before_submit
and on_submit; an UPDATE that skipped them would be worse than the refusal.

So the request threw, a red toast appeared for a moment on a phone, and the
document stayed a draft. The approver believed they had approved it. The
employee was asked to submit it again. Nothing was recorded anywhere.

BLAST RADIUS is wider than the report:

  Submit  broken for Attendance Request, OT Request, Replacement Leave Claim —
          the three doctypes with no decision field, which therefore miss the
          `DECIDE_THEN_SUBMIT` path that already routes through `decide`.
  Cancel  broken for EVERY doctype in the sheet. Cancel sends no status, so it
          always fell to the same setValue branch.

`decide` cannot serve these: it exists to write a decision FIELD, and these
doctypes have none — for them submission IS the decision.

Bench-free: the contract is read from the AST. Run it as a FILE:

    python3 hrms/api/test_approval.py
"""

import ast
import pathlib
import unittest

API = pathlib.Path(__file__).resolve().parent / "approval.py"
SHEET = pathlib.Path(__file__).resolve().parents[2] / "frontend/src/components/RequestActionSheet.vue"


def _fn(name):
	tree = ast.parse(API.read_text())
	fn = next(
		(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name),
		None,
	)
	assert fn is not None, f"approval.{name} is missing"
	return fn


class TestFinalizeExists(unittest.TestCase):
	def setUp(self):
		self.fn = _fn("finalize")

	def test_it_is_whitelisted_for_post(self):
		"""A state transition is not a GET, and an unwhitelisted one is a 404
		from the browser — the same silent nothing this replaces."""
		decorators = " ".join(ast.dump(d) for d in self.fn.decorator_list)
		self.assertIn("whitelist", decorators)
		self.assertIn("POST", decorators)

	def test_it_calls_the_real_transitions(self):
		"""doc.submit() and doc.cancel(), not a field write. That distinction is
		the entire bug: the transition runs validate, before_submit and
		on_submit, and an UPDATE that skipped them would let an OT Request past
		validate_self_submission and validate_mandatory_attachment."""
		called = {
			n.func.attr
			for n in ast.walk(self.fn)
			if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
		}
		self.assertIn("submit", called)
		self.assertIn("cancel", called)

	def test_it_checks_permission(self):
		called = {
			n.func.attr
			for n in ast.walk(self.fn)
			if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
		}
		self.assertIn("check_permission", called)

	def test_it_locks_the_row_before_reading_state(self):
		"""Same reasoning as `decide`: two taps, or two approvers, must not both
		read docstatus 0 and both proceed. `decide` takes the lock first and this
		must too, or the fix reintroduces the race next door."""
		src = ast.unparse(self.fn)
		self.assertIn("for_update=True", src)

	def test_an_already_final_document_is_not_an_error(self):
		"""Two taps on a phone are one intention. The second must report the
		first one's outcome, not throw at somebody who did nothing wrong.

		Asserted as behaviour — an early return guarded by a docstatus
		comparison — rather than as a literal string. The first version of this
		test pinned `docstatus == 1` and went red when the check was generalised
		to compare against the REQUESTED transition, which is strictly better."""
		src = ast.unparse(self.fn)
		self.assertIn("doc.docstatus == docstatus", src)
		guard = src.index("doc.docstatus == docstatus")
		self.assertIn(
			"return _state(doc)",
			src[guard : guard + 260],
			"an already-final document must return its state, not fall through",
		)


class TestStateHandlesDoctypesWithNoDecisionField(unittest.TestCase):
	"""`_state` indexed DECIDE_THEN_SUBMIT unconditionally.

	Safe while `decide` was its only caller — every doctype `decide` serves is
	in that map. `finalize` exists precisely FOR the doctypes that are not, so
	it raised KeyError AFTER a successful doc.submit(): the transition ran, the
	response builder crashed, and the rollback undid the approval.

	The endpoint written to fix a silent non-approval would have produced one.
	Caught on a real bench, not by reading.
	"""

	def test_it_does_not_index_the_map_unconditionally(self):
		src = ast.unparse(_fn("_state"))
		self.assertNotIn(
			"DECIDE_THEN_SUBMIT[doc.doctype]",
			src,
			"a doctype with no decision field must not KeyError",
		)

	def test_it_looks_the_doctype_up_safely(self):
		src = ast.unparse(_fn("_state"))
		self.assertIn("DECIDE_THEN_SUBMIT.get(", src)


class TestTheSheetUsesIt(unittest.TestCase):
	"""The endpoint is worthless if the button still calls setValue."""

	def test_the_action_sheet_no_longer_writes_docstatus_through_setvalue(self):
		src = SHEET.read_text()
		offending = [line.strip() for line in src.splitlines() if "setValue" in line and "docstatus" in line]
		self.assertEqual(offending, [], f"setValue still carries docstatus: {offending}")

	def test_the_sheet_calls_the_finalize_endpoint(self):
		self.assertIn("hrms.api.approval.finalize", SHEET.read_text())


if __name__ == "__main__":
	unittest.main()
