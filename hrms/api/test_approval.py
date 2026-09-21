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
import re
import unittest

API = pathlib.Path(__file__).resolve().parent / "approval.py"
SHEET = pathlib.Path(__file__).resolve().parents[2] / "frontend/src/components/RequestActionSheet.vue"
# parents[1] is the hrms/ app root (the Desk bundle lives under hrms/public, not the
# repo root). parents[2] pointed at a nonexistent repo-root path, so read_text raised
# FileNotFoundError and the Desk<->Python parity guard silently never ran.
DESK_JS = pathlib.Path(__file__).resolve().parents[1] / "public/js/utils/request_approval.js"


def _decide_then_submit_keys():
	"""The keys of approval.DECIDE_THEN_SUBMIT, read from the AST so a status string
	quoted inside a comment cannot be mistaken for a doctype."""
	tree = ast.parse(API.read_text())
	for node in ast.walk(tree):
		if isinstance(node, ast.Assign) and any(
			isinstance(t, ast.Name) and t.id == "DECIDE_THEN_SUBMIT" for t in node.targets
		):
			return {k.value for k in node.value.keys}
	raise AssertionError("DECIDE_THEN_SUBMIT not found in approval.py")


def _array_items(text, marker):
	"""The quoted strings of the array literal that follows `marker`."""
	block = text.split(marker, 1)[1].split("]", 1)[0]
	return set(re.findall(r'"([^"]+)"', block))


class TestDecideDoctypeListsAgree(unittest.TestCase):
	"""approval.DECIDE_THEN_SUBMIT is the authority for which requests decide-then-
	submit. The Desk client script keeps a copy — it can only wire form handlers to
	named doctypes — and it must stay set-equal, or a doctype loses its Desk approve
	buttons or gets them where decide would reject. The PWA keeps NO copy: it sends
	every decision to decide and lets the server's allow-list rule, so the third copy
	(and the setValue fallback beside it) that used to strand approvals is gone."""

	def test_desk_js_matches_the_python_map(self):
		py = _decide_then_submit_keys()
		js = _array_items(DESK_JS.read_text(), "DECIDE_DOCTYPES = [")
		self.assertEqual(py, js, "Desk DECIDE_DOCTYPES drifted from approval.DECIDE_THEN_SUBMIT")

	def test_the_pwa_sheet_keeps_no_decide_list_or_setvalue_fallback(self):
		src = SHEET.read_text()
		self.assertNotIn("DECIDE_THEN_SUBMIT", src, "the PWA sheet must not reintroduce a decide list")
		self.assertNotIn("setValue.submit", src, "a decision must go through decide, never setValue")


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


class TestApprovalIsAuthorisedByRouting(unittest.TestCase):
	"""A team lead with only the Employee role could not approve anything.

	FOUND BY RUNNING AS A REAL USER, after the operator stopped trusting green
	suites — and they were right. The earlier verification of decide/finalize ran
	as Administrator, which proves nothing about the person the work actually
	routes to. As the lead:

	    worker=nurul.aisyah@...  lead=test2@example.com  lead roles=['Employee']
	    Attendance Request   APPROVE FAILED: PermissionError

	The whole approver model routes by DATA — reports_to, the approver fields,
	Department Approver rows. is_approver() computes it, notifications deliver
	to it, the Team tab renders for it. But decide() ended in doc.submit(),
	which checks ROLE permission — and a reporting manager holding only
	Employee has no submit on OT Request, Attendance Request or Replacement
	Leave Claim. Every surface delivered the work; the last line refused it.

	The precedent is already in this repo: remote_checkin._decide authorises by
	_ensure_approver (are you the routed approver, or HR?) and then transitions
	with ignore_permissions. Roles are not the gate there; routing is. decide
	and finalize now follow it: verify the caller is the routed approver, then
	elevate ONLY the transition. Validators still run — validate_self_submission
	reads session.user and still refuses self-approval.
	"""

	def setUp(self):
		self.tree = ast.parse(API.read_text())

	def _fn(self, name):
		fn = next(
			(n for n in ast.walk(self.tree) if isinstance(n, ast.FunctionDef) and n.name == name),
			None,
		)
		assert fn is not None, f"approval.{name} is missing"
		return fn

	def test_there_is_a_routed_approver_check(self):
		fn = self._fn("_is_routed_approver")
		src = ast.unparse(fn)
		# The three routing shapes: named approver field, reports_to, HR.
		self.assertIn("reports_to", src)
		self.assertIn("APPROVER_FIELD", src)

	def test_hr_approval_is_bounded_by_the_company_fence(self):
		"""An HR operator decides only inside their company fence — otherwise a
		fenced HR (Company A) could decide a Company B request whose row the
		fence hides from every list. company_visible is True for unfenced HR, so
		admin/unfenced behaviour is unchanged."""
		src = ast.unparse(self._fn("_is_routed_approver"))
		self.assertIn("company_visible", src)

	def test_legacy_finalize_routes_submit_and_approved_cancel(self):
		"""AMENDED 14 Sep 2026, owner ruling: HR and the approver may cancel an
		approved request; the employee may not.

		Submit authority is routed through `_decision_access`. The cancel branch
		asks `_is_routed_approver` directly again — excluding the request's own
		employee — so a reports_to manager holding only Employee (no `cancel`
		DocPerm) can cancel what they approved. The exact shape is pinned in
		hrms/tests/test_cancel_is_not_a_routing_right.py."""
		called = {
			n.func.id
			for n in ast.walk(self._fn("finalize"))
			if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
		}
		self.assertIn(
			"_decision_access",
			called,
			"finalize must still route its submit authority through the decision gate",
		)
		# Amended 17 Sep 2026. finalize used to re-derive who may cancel — "not
		# the owner, and routed" — which is precisely how the owner was left
		# out when the owner became allowed to withdraw. It asks the ONE copy
		# now, and the test asks for that instead of for the copy.
		self.assertIn(
			"may_cancel",
			called,
			"an approved cancel asks the guard who may cancel; it does not re-derive it",
		)

	# Public native tests exercise denial and routed elevation through both
	# endpoints; a source-position assertion cannot follow their shared gate.


class TestTheSheetUsesIt(unittest.TestCase):
	"""The endpoint is worthless if the button still calls setValue."""

	def test_the_action_sheet_no_longer_writes_docstatus_through_setvalue(self):
		src = SHEET.read_text()
		offending = [line.strip() for line in src.splitlines() if "setValue" in line and "docstatus" in line]
		self.assertEqual(offending, [], f"setValue still carries docstatus: {offending}")

	def test_the_sheet_calls_the_finalize_endpoint(self):
		self.assertIn("hrms.api.approval.finalize", SHEET.read_text())


class TestFinalizeCancelByTheApprover(unittest.TestCase):
	"""Owner ruling, 14 Sep 2026: HR and the approver may cancel an approved
	request. A reports_to manager usually holds only Employee — no `cancel`
	DocPerm — so finalize elevates the CANCEL for a routed approver who is not the
	request's own employee. Runs finalize itself against the frappe stub."""

	APPROVER = "manager@example.com"
	STAFF_USER = "staff@example.com"

	@classmethod
	def setUpClass(cls):
		import sys
		from unittest.mock import MagicMock, patch

		sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
		import _erpnext_stub
		import _frappe_stub

		_frappe_stub.install()
		_erpnext_stub.install()
		import frappe

		from hrms.api import approval

		cls.frappe, cls.approval, cls.MagicMock, cls.patch = frappe, approval, MagicMock, patch

	def _finalize(self, user, stored="Approved", can_cancel=False, routed=True):
		frappe, approval = self.frappe, self.approval
		doc = frappe._dict(
			doctype="Leave Application",
			name="HR-LAP-0001",
			docstatus=1,
			employee="HR-EMP-STAFF",
			modified="2026-09-14 10:00:00",
			flags=frappe._dict(),
		)
		doc.check_permission = lambda ptype: None
		doc.cancel = lambda: doc.update(docstatus=2, flags_at_cancel=dict(doc.flags))

		def get_value(doctype, name, fieldname, **kw):
			if doctype == "Employee" and fieldname == "user_id":
				return self.STAFF_USER
			return 1 if fieldname == "docstatus" else stored

		db = self.MagicMock()
		db.exists.return_value = True
		db.get_value.side_effect = get_value
		patch = self.patch
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "get_doc", return_value=doc),
			patch.object(frappe, "has_permission", return_value=can_cancel, create=True),
			patch.object(frappe, "session", frappe._dict(user=user)),
			patch.object(approval, "_request_read_allowed", return_value=True),
			patch.object(approval, "_is_routed_approver", return_value=routed),
		):
			approval.finalize(doc.doctype, doc.name, 2)
		return doc

	def test_a_routed_approver_without_cancel_permission_is_elevated_and_cancels(self):
		doc = self._finalize(self.APPROVER)
		self.assertEqual(doc.docstatus, 2)
		self.assertIs(doc.flags_at_cancel.get("ignore_permissions"), True)

	def test_the_employee_is_elevated_to_withdraw_their_own(self):
		"""Amended 17 Sep 2026. This asserted the owner was refused — which is
		what made the guard's new permission unreachable: it said yes, and this
		endpoint, the only way the app cancels, said no."""
		doc = self._finalize(self.STAFF_USER)
		self.assertEqual(doc.docstatus, 2)
		self.assertTrue(doc.flags_at_cancel.get("ignore_permissions"))

	def test_someone_not_routed_is_not_elevated(self):
		with self.assertRaises(self.frappe.PermissionError):
			self._finalize(self.APPROVER, routed=False)

	def test_a_rejected_request_stays_governed_by_the_cancel_permission(self):
		with self.assertRaises(self.frappe.PermissionError):
			self._finalize(self.APPROVER, stored="Rejected")

	def test_a_holder_of_cancel_permission_is_not_elevated(self):
		doc = self._finalize(self.APPROVER, can_cancel=True)
		self.assertEqual(doc.docstatus, 2)
		self.assertFalse(doc.flags_at_cancel.get("ignore_permissions"))


class TestFinalizeOnlyTransitionsRequestDoctypes(unittest.TestCase):
	"""Audit 21 Sep 2026, H4. `finalize` had no doctype allow-list, so a PWA
	session could submit or cancel ANY submittable doctype (Salary Slip, Payroll
	Entry, Journal Entry) with nothing but the native perm. Refused up front, by
	name, before any DB read — the same shape as `decide` and `cancel_for_correction`."""

	@classmethod
	def setUpClass(cls):
		import sys
		from unittest.mock import MagicMock, patch

		sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
		import _erpnext_stub
		import _frappe_stub

		_frappe_stub.install()
		_erpnext_stub.install()
		import frappe

		from hrms.api import approval

		cls.frappe, cls.approval, cls.MagicMock, cls.patch = frappe, approval, MagicMock, patch

	def test_a_salary_slip_is_refused_before_any_db_read(self):
		db = self.MagicMock()
		with (
			self.patch.object(self.frappe, "db", db),
			self.assertRaises(self.frappe.ValidationError) as ctx,
		):
			self.approval.finalize("Salary Slip", "Sal Slip/HR-EMP-0001/00001", 1)
		self.assertIn("Salary Slip", str(ctx.exception))
		db.exists.assert_not_called()
		db.get_value.assert_not_called()

	def test_every_request_doctype_is_still_served(self):
		from hrms.utils.approved_request_guard import DECISION_FIELD_BY_DOCTYPE

		tree = ast.parse(API.read_text())
		fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "finalize")
		names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
		self.assertIn("DECISION_FIELD_BY_DOCTYPE", names, "finalize must gate on the request allow-list")
		self.assertIn("Employee Advance", DECISION_FIELD_BY_DOCTYPE)


class TestCanCancelApproved(unittest.TestCase):
	"""Hotfix 14 Sep 2026: a reports_to-only manager saw no Cancel on an approved
	request (PWA and Desk) although the guard lets them cancel it. The read
	endpoint answers with the guard's own decision — no second copy of the rule."""

	CALLER = "manager@example.com"
	STAFF_USER = "staff@example.com"
	# Amended 17 Sep 2026: the employee may withdraw their own, so the refusal
	# names all three of the people who can.
	MESSAGE = "Only you, HR or your approver can cancel an approved request."
	PAID = (
		"This overtime is already paid in a submitted salary slip. "
		"Correct it with a payroll adjustment instead."
	)

	@classmethod
	def setUpClass(cls):
		TestFinalizeCancelByTheApprover.setUpClass.__func__(cls)

	def _ask(
		self,
		doctype="Leave Application",
		stored="Approved",
		docstatus=1,
		roles=("Employee",),
		own_employee=None,
		reports_to=None,
		readable=True,
		paid_slip=None,
		**fields,
	):
		from unittest.mock import patch

		frappe, approval = self.frappe, self.approval
		doc = frappe._dict(
			doctype=doctype, name="REQ-1", docstatus=docstatus, employee="HR-EMP-STAFF", **fields
		)
		employee_user = self.CALLER if own_employee == "HR-EMP-STAFF" else self.STAFF_USER

		def get_value(dt, name=None, fieldname=None, **kw):
			if dt == doctype and name == "REQ-1" and isinstance(fieldname, str):
				return stored
			if dt == "OT Request":
				return frappe._dict(
					employee="HR-EMP-STAFF", ot_date="2026-08-20", compensation="Overtime Pay"
				)
			if dt == "Salary Slip":
				return paid_slip
			if dt == "Employee":
				return {"user_id": employee_user, "company": "Company A", "reports_to": reports_to}[fieldname]
			return None

		db = self.MagicMock()
		db.get_value.side_effect = get_value
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "get_doc", return_value=doc),
			patch.object(frappe, "get_roles", return_value=list(roles), create=True),
			patch.object(frappe, "flags", frappe._dict(), create=True),
			patch.object(frappe, "session", frappe._dict(user=self.CALLER)),
			patch.object(approval, "_request_read_allowed", return_value=readable),
			patch("hrms.overrides.company_scope.company_visible", return_value=True),
			patch("hrms.utils.identity.own_employees", return_value=[own_employee] if own_employee else []),
		):
			return approval.can_cancel_approved(doctype, "REQ-1")

	def test_the_reports_to_manager_may_cancel(self):
		for doctype in ("Leave Application", "OT Request", "Attendance Request", "Travel Request"):
			with self.subTest(doctype=doctype):
				stored = None if doctype == "Travel Request" else "Approved"
				self.assertEqual(
					self._ask(doctype, stored=stored, own_employee="HR-EMP-MGR", reports_to="HR-EMP-MGR"),
					{"can_cancel": True, "reason": None},
				)

	def test_hr_and_the_named_approver_may_cancel(self):
		self.assertEqual(self._ask(roles=("HR User",)), {"can_cancel": True, "reason": None})
		self.assertEqual(
			self._ask(leave_approver=self.CALLER, own_employee="HR-EMP-MGR"),
			{"can_cancel": True, "reason": None},
		)

	def test_the_employee_may_withdraw_their_own(self):
		"""Amended 17 Sep 2026 — this asserted they could not, until the owner
		answered "withdrawal. a." The screen must offer the button, or the
		guard's new permission is one nobody can reach."""
		self.assertEqual(
			self._ask(
				roles=("HR Manager",),
				own_employee="HR-EMP-STAFF",
				from_date="2026-08-20",
				to_date="2026-08-20",
			),
			{"can_cancel": True, "reason": None},
		)

	def test_an_unrouted_viewer_may_not(self):
		self.assertEqual(
			self._ask(own_employee="HR-EMP-OTHER", reports_to="HR-EMP-MGR"),
			{"can_cancel": False, "reason": self.MESSAGE},
		)

	def test_paid_overtime_is_refused_even_for_hr(self):
		self.assertEqual(
			self._ask("OT Request", roles=("HR Manager",), paid_slip="Sal Slip/1"),
			{"can_cancel": False, "reason": self.PAID},
		)

	def test_a_request_that_is_not_approved_and_submitted_is_not_its_business(self):
		for kwargs in ({"stored": "Rejected"}, {"stored": "Open"}, {"docstatus": 0}, {"docstatus": 2}):
			with self.subTest(**kwargs):
				self.assertEqual(
					self._ask(roles=("HR Manager",), **kwargs), {"can_cancel": False, "reason": None}
				)
		self.assertEqual(
			self._ask("Salary Slip", roles=("HR Manager",)), {"can_cancel": False, "reason": None}
		)

	def test_a_request_the_caller_cannot_read_is_refused(self):
		with self.assertRaises(self.frappe.PermissionError):
			self._ask(roles=("HR Manager",), readable=False)

	def test_it_is_a_whitelisted_read_sharing_the_guard(self):
		fn = _fn("can_cancel_approved")
		decorators = [ast.unparse(d) for d in fn.decorator_list]
		self.assertTrue(any(d.startswith("frappe.whitelist") for d in decorators), decorators)
		self.assertNotIn("POST", "".join(decorators))
		src = ast.unparse(fn)
		self.assertIn("cancel_refusal(", src)
		self.assertIn("_request_read_allowed(", src)
		self.assertNotIn("_is_routed_approver(", src, "the rule lives in cancel_refusal only")


DESK_CANCEL_JS = pathlib.Path(__file__).resolve().parents[1] / "public/js/utils/approved_request_cancel.js"


class TestDeskApprovedCancelWiring(unittest.TestCase):
	def test_desk_doctypes_match_the_guard_map(self):
		guard = pathlib.Path(__file__).resolve().parents[1] / "utils/approved_request_guard.py"
		tree = ast.parse(guard.read_text())
		keys = next(
			{k.value for k in n.value.keys}
			for n in ast.walk(tree)
			if isinstance(n, ast.Assign)
			and any(getattr(t, "id", None) == "DECISION_FIELD_BY_DOCTYPE" for t in n.targets)
		)
		js = _array_items(DESK_CANCEL_JS.read_text(), "APPROVED_CANCEL_DOCTYPES = [")
		self.assertEqual(keys, js)

	def test_it_ships_in_the_desk_bundle(self):
		bundle = pathlib.Path(__file__).resolve().parents[1] / "public/js/hrms.bundle.js"
		self.assertIn('import "./utils/approved_request_cancel";', bundle.read_text())


if __name__ == "__main__":
	unittest.main()
