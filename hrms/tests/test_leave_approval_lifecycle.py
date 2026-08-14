"""One approval action, one canonical final state — for every persona.

HR reported that an approved Leave Application "remains in a state that requires
an HR Manager to submit or resubmit it manually". Reproduced on a disposable v16
site before the fix:

    reject, named approver   -> docstatus 0, status Rejected, 0 ledger entries
    approve (status only)    -> docstatus 0, status Approved, 0 ledger entries
    then HR submits again    -> docstatus 1, status Approved, 1 ledger entry

The decision and the submission are one transition, not two — each of the three
decide-then-submit doctypes says so in its own `on_submit`, and the decision
field is `reqd`, `no_copy` and not `allow_on_submit`, so it cannot be set
afterwards. There is no legal resting state where a request is decided but
still a draft. `hrms.api.approval.decide` is that transition, server-side.

Every test below asserts the full observable state — `docstatus`, the decision
field, and the Leave Ledger — because "the status says Approved" was exactly the
half-truth that hid this defect.

Bench-backed. Run with:
    bench --site <site> run-tests --module hrms.tests.test_leave_approval_lifecycle
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, getdate, nowdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api.approval import DECIDE_THEN_SUBMIT, decide, report_half_transitioned

test_dependencies = ["Employee", "Leave Type"]

COMPANY = "_Test Company"
LEAVE_TYPE = "_Test Leave Type"

EMPLOYEE = "leave_lc_employee@example.com"
APPROVER = "leave_lc_approver@example.com"
OUTSIDER = "leave_lc_outsider@example.com"
HR_USER = "leave_lc_hruser@example.com"
HR_MANAGER = "leave_lc_hrmanager@example.com"
SYS_MANAGER = "leave_lc_sysmanager@example.com"


def grant(user: str, *roles: str) -> None:
	doc = frappe.get_doc("User", user)
	doc.flags.ignore_permissions = True
	doc.add_roles(*roles)
	frappe.clear_cache(user=user)


def unfence(user: str) -> None:
	"""Drop the `allow=Employee` User Permission `make_employee` leaves behind.

	It scopes the user to their OWN employee record, which is right for staff and
	wrong for an HR fixture: `validate_leave_access` asks for `read` on the
	applicant's Employee, and with that permission in place an HR User is refused
	their own job. Real HR users are not anchored this way; the fixture was.
	"""
	frappe.db.delete("User Permission", {"user": user, "allow": "Employee"})
	frappe.clear_cache(user=user)


def state(name: str) -> dict:
	"""Everything that matters, in one read. A test that checks only `status`
	is the reason this defect survived."""
	row = (
		frappe.db.get_value(
			"Leave Application", name, ["docstatus", "status", "leave_approver"], as_dict=True
		)
		or {}
	)
	row["ledger"] = frappe.db.count("Leave Ledger Entry", {"transaction_name": name, "docstatus": 1})
	return row


class _LeaveLifecycleCase(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		from hrms.hr.doctype.leave_application.test_leave_application import make_allocation_record

		frappe.set_user("Administrator")
		cls.employee = make_employee(EMPLOYEE, company=COMPANY)
		cls.approver = make_employee(APPROVER, company=COMPANY)
		cls.outsider = make_employee(OUTSIDER, company=COMPANY)
		make_employee(HR_USER, company=COMPANY)
		make_employee(HR_MANAGER, company=COMPANY)
		make_employee(SYS_MANAGER, company=COMPANY)

		frappe.db.set_value("Employee", cls.employee, "leave_approver", APPROVER)
		grant(APPROVER, "Leave Approver")
		grant(OUTSIDER, "Leave Approver")
		grant(HR_USER, "HR User")
		grant(HR_MANAGER, "HR Manager")
		grant(SYS_MANAGER, "System Manager")
		for hr in (HR_USER, HR_MANAGER):
			unfence(hr)

		make_allocation_record(
			employee=cls.employee,
			leave_type=LEAVE_TYPE,
			from_date=add_months(nowdate(), -6),
			to_date=add_months(nowdate(), 6),
		)

	def setUp(self):
		# Per-CLASS rollback is what IntegrationTestCase gives; a named savepoint
		# undoes only this test without taking the fixtures above with it.
		frappe.db.savepoint("leave_lifecycle")
		self.addCleanup(frappe.db.rollback, save_point="leave_lifecycle")
		self.addCleanup(frappe.set_user, "Administrator")

	def draft(self, offset: int = 5, employee: str | None = None, approver: str = APPROVER) -> str:
		"""What an employee's saved request looks like: draft + Open.

		In this fork the draft IS the pending-approval state — the Employee and
		Employee Self Service roles hold no `submit` right, and
		`on_update` notifies the approver precisely on `status == "Open" and
		docstatus < 1`.
		"""
		frappe.set_user("Administrator")
		doc = frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": employee or self.employee,
				"leave_type": LEAVE_TYPE,
				"from_date": add_days(getdate(), offset),
				"to_date": add_days(getdate(), offset),
				"company": COMPANY,
				"leave_approver": approver,
				"status": "Open",
			}
		)
		doc.insert(ignore_permissions=True)
		return doc.name


class TestLeaveDecisionReachesFinalState(_LeaveLifecycleCase):
	def test_employee_draft_is_the_pending_state(self):
		name = self.draft()
		self.assertEqual(
			state(name), {"docstatus": 0, "status": "Open", "leave_approver": APPROVER, "ledger": 0}
		)

	def test_one_approval_reaches_the_final_state(self):
		name = self.draft()
		frappe.set_user(APPROVER)

		result = decide("Leave Application", name, "Approved")

		self.assertEqual(result["docstatus"], 1)
		self.assertEqual(result["status"], "Approved")
		self.assertEqual(
			state(name), {"docstatus": 1, "status": "Approved", "leave_approver": APPROVER, "ledger": 1}
		)

	def test_hr_does_not_have_to_submit_again(self):
		"""The complaint, stated as an assertion.

		The second Submit step appears exactly when a request is decided and
		still a draft. After one approval that condition is false, so there is
		nothing for HR to press — and a redundant `decide` adds no second ledger
		effect either.
		"""
		name = self.draft()
		frappe.set_user(APPROVER)
		decide("Leave Application", name, "Approved")

		frappe.set_user(HR_MANAGER)
		doc = frappe.get_doc("Leave Application", name)
		self.assertFalse(
			doc.docstatus == 0 and doc.status in ("Approved", "Rejected"),
			"the request is still decided-but-draft, so HR must submit it again",
		)
		self.assertEqual(doc.docstatus, 1)

		decide("Leave Application", name, "Approved")
		self.assertEqual(state(name)["ledger"], 1)

	def test_rejection_also_reaches_the_final_state(self):
		"""The path that ALWAYS half-transitioned before: the old client-side
		coupling fired on "Approved" only."""
		name = self.draft(6)
		frappe.set_user(APPROVER)

		decide("Leave Application", name, "Rejected")

		self.assertEqual(
			state(name), {"docstatus": 1, "status": "Rejected", "leave_approver": APPROVER, "ledger": 0}
		)

	def test_approval_writes_exactly_one_ledger_effect(self):
		name = self.draft(7)
		frappe.set_user(APPROVER)
		decide("Leave Application", name, "Approved")

		entries = frappe.get_all(
			"Leave Ledger Entry",
			filters={"transaction_name": name, "docstatus": 1},
			fields=["leaves", "employee", "leave_type"],
		)
		self.assertEqual(len(entries), 1)
		self.assertEqual(entries[0].leaves, -1.0)
		self.assertEqual(entries[0].employee, self.employee)

	def test_no_decided_draft_survives_the_transition(self):
		name = self.draft(8)
		frappe.set_user(APPROVER)
		decide("Leave Application", name, "Approved")

		frappe.set_user("Administrator")
		self.assertEqual(report_half_transitioned("Leave Application")["Leave Application"]["count"], 0)


class TestIdempotencyAndRetries(_LeaveLifecycleCase):
	def test_repeated_approval_is_a_no_op(self):
		name = self.draft()
		frappe.set_user(APPROVER)

		first = decide("Leave Application", name, "Approved")
		second = decide("Leave Application", name, "Approved")

		self.assertEqual(first, second)
		self.assertEqual(state(name)["ledger"], 1, "a retry duplicated the ledger effect")

	def test_three_taps_still_produce_one_ledger_entry(self):
		name = self.draft(9)
		frappe.set_user(APPROVER)
		for _ in range(3):
			decide("Leave Application", name, "Approved")
		self.assertEqual(state(name)["ledger"], 1)

	def test_reversing_a_decision_is_refused(self):
		"""Undoing an approval is a cancellation, with its own permission and
		its own ledger reversal — not a second decision."""
		name = self.draft(10)
		frappe.set_user(APPROVER)
		decide("Leave Application", name, "Approved")

		with self.assertRaises(frappe.ValidationError):
			decide("Leave Application", name, "Rejected")
		self.assertEqual(state(name)["status"], "Approved")

	def test_a_cancelled_request_cannot_be_decided(self):
		name = self.draft(11)
		frappe.set_user(APPROVER)
		decide("Leave Application", name, "Approved")
		frappe.get_doc("Leave Application", name).cancel()

		with self.assertRaises(frappe.ValidationError):
			decide("Leave Application", name, "Approved")


class TestAuthorization(_LeaveLifecycleCase):
	def test_ordinary_employee_cannot_decide_their_own_request(self):
		name = self.draft()
		frappe.set_user(EMPLOYEE)
		with self.assertRaises((frappe.PermissionError, frappe.ValidationError)):
			decide("Leave Application", name, "Approved")
		self.assertEqual(state(name)["docstatus"], 0)

	def test_unrelated_approver_is_denied(self):
		"""Holding the Leave Approver role is not authority over somebody
		else's request — the row scope names the approver."""
		name = self.draft(6)
		frappe.set_user(OUTSIDER)
		with self.assertRaises(frappe.PermissionError):
			decide("Leave Application", name, "Approved")
		self.assertEqual(
			state(name), {"docstatus": 0, "status": "Open", "leave_approver": APPROVER, "ledger": 0}
		)

	def test_system_manager_without_hr_authority_is_denied(self):
		"""System Manager is technical. It carries no sight of, or authority
		over, another team's leave."""
		name = self.draft(7)
		frappe.set_user(SYS_MANAGER)
		with self.assertRaises(frappe.PermissionError):
			decide("Leave Application", name, "Approved")
		self.assertEqual(state(name)["docstatus"], 0)

	def test_hr_user_may_decide(self):
		name = self.draft(8)
		frappe.set_user(HR_USER)
		decide("Leave Application", name, "Approved")
		self.assertEqual(
			state(name), {"docstatus": 1, "status": "Approved", "leave_approver": APPROVER, "ledger": 1}
		)

	def test_hr_manager_may_decide(self):
		name = self.draft(9)
		frappe.set_user(HR_MANAGER)
		decide("Leave Application", name, "Rejected")
		self.assertEqual(state(name)["docstatus"], 1)

	def test_administrator_may_decide(self):
		name = self.draft(10)
		frappe.set_user("Administrator")
		decide("Leave Application", name, "Approved")
		self.assertEqual(state(name)["docstatus"], 1)

	def test_cross_company_hr_user_is_denied(self):
		"""An HR user fenced to another company must not reach this request.

		Skipped rather than faked when the site has only one company: an
		assertion that cannot be about a real second company proves nothing.
		"""
		other = frappe.db.get_value("Company", {"name": ("!=", COMPANY)}, "name")
		if not other:
			self.skipTest("single-company site — no cross-company scope to test")

		name = self.draft(11)
		foreign = "leave_lc_foreign_hr@example.com"
		make_employee(foreign, company=other)
		grant(foreign, "HR User")
		frappe.db.delete("User Permission", {"user": foreign, "allow": "Company"})
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": foreign,
				"allow": "Company",
				"for_value": other,
				"apply_to_all_doctypes": 1,
			}
		).insert(ignore_permissions=True)
		frappe.clear_cache(user=foreign)

		frappe.set_user(foreign)
		with self.assertRaises((frappe.PermissionError, frappe.ValidationError)):
			decide("Leave Application", name, "Approved")
		self.assertEqual(state(name)["docstatus"], 0)

	def test_an_arbitrary_doctype_cannot_be_driven_through_decide(self):
		"""`decide` is whitelisted, so its doctype list has to be an allow-list
		rather than something the caller supplies."""
		frappe.set_user(HR_MANAGER)
		with self.assertRaises(frappe.ValidationError):
			decide("Employee", self.employee, "Approved")

	def test_only_approved_or_rejected_are_decisions(self):
		name = self.draft(12)
		frappe.set_user(APPROVER)
		for value in ("Open", "Cancelled", "Whatever"):
			with self.assertRaises(frappe.ValidationError):
				decide("Leave Application", name, value)
		self.assertEqual(state(name)["status"], "Open")


class TestTransactionality(_LeaveLifecycleCase):
	def test_a_failing_downstream_step_leaves_no_partial_state(self):
		"""If anything after the decision fails, the decision must not survive.

		The failure is injected into `create_leave_ledger_entry`, i.e. after
		validation and after the decision field is set — precisely the window
		that used to produce "Approved but draft".
		"""
		from unittest.mock import patch

		name = self.draft()
		frappe.set_user(APPROVER)

		frappe.db.savepoint("before_decide")
		with patch(
			"hrms.hr.doctype.leave_application.leave_application.LeaveApplication.create_leave_ledger_entry",
			side_effect=RuntimeError("ledger unavailable"),
		):
			with self.assertRaises(RuntimeError):
				decide("Leave Application", name, "Approved")

		# what Frappe does to a request that raised: roll the whole thing back
		frappe.db.rollback(save_point="before_decide")

		self.assertEqual(
			state(name),
			{"docstatus": 0, "status": "Open", "leave_approver": APPROVER, "ledger": 0},
			"a failed downstream step left the request partially transitioned",
		)

	def test_cancellation_reverses_the_ledger(self):
		name = self.draft(6)
		frappe.set_user(APPROVER)
		decide("Leave Application", name, "Approved")
		self.assertEqual(state(name)["ledger"], 1)

		frappe.get_doc("Leave Application", name).cancel()

		after = frappe.db.get_value("Leave Application", name, ["docstatus", "status"], as_dict=True)
		self.assertEqual(after.docstatus, 2)
		self.assertEqual(after.status, "Cancelled")
		# `create_leave_ledger_entry(submit=False)` routes to `delete_ledger_entry`,
		# so the reversal removes the rows rather than cancelling them.
		self.assertEqual(
			frappe.db.count("Leave Ledger Entry", {"transaction_name": name}),
			0,
			"the ledger effect outlived the cancellation",
		)

	def test_amendment_starts_undecided(self):
		"""`status` is no_copy, so an amended draft cannot inherit a decision —
		the amendment has to be decided on its own merits."""
		name = self.draft(7)
		frappe.set_user(APPROVER)
		decide("Leave Application", name, "Approved")
		frappe.get_doc("Leave Application", name).cancel()

		frappe.set_user(HR_MANAGER)
		# What the Desk's Amend button does: copy respecting `no_copy`, then
		# reset to draft. `frappe.copy_doc` keeps `docstatus` under `frappe.in_test`
		# specifically, so a test that omits this amends a *cancelled* document.
		amended = frappe.copy_doc(frappe.get_doc("Leave Application", name), ignore_no_copy=False)
		amended.amended_from = name
		amended.docstatus = 0
		amended.from_date = add_days(getdate(), 20)
		amended.to_date = add_days(getdate(), 20)
		amended.insert()

		self.assertEqual(amended.docstatus, 0)
		self.assertNotIn(amended.status, ("Approved", "Rejected"))


class TestMirroredEmployee(_LeaveLifecycleCase):
	"""ERP-owned rows stay ERP-owned. Approving here would move leave balances
	this site does not own and would be invisible to `hrms.sync.parity`."""

	def test_a_mirrored_employees_request_cannot_be_decided_here(self):
		name = self.draft(8)
		frappe.db.set_value(
			"Employee", self.employee, "synced_from_instance", "test-source", update_modified=False
		)
		self.addCleanup(
			frappe.db.set_value,
			"Employee",
			self.employee,
			"synced_from_instance",
			None,
			update_modified=False,
		)

		frappe.set_user(APPROVER)
		with self.assertRaises(frappe.PermissionError):
			decide("Leave Application", name, "Approved")

		self.assertEqual(
			state(name), {"docstatus": 0, "status": "Open", "leave_approver": APPROVER, "ledger": 0}
		)


class TestHalfTransitionedReport(_LeaveLifecycleCase):
	def test_it_finds_a_decided_draft_and_repairs_nothing(self):
		name = self.draft()
		# the exact shape the old client-side coupling produced
		frappe.db.set_value("Leave Application", name, "status", "Approved", update_modified=False)

		frappe.set_user(HR_MANAGER)
		found = report_half_transitioned("Leave Application")["Leave Application"]

		self.assertEqual(found["count"], 1)
		self.assertEqual(found["rows"][0]["name"], name)
		self.assertEqual(state(name)["docstatus"], 0, "the report submitted a historical row")
		self.assertEqual(state(name)["ledger"], 0)

	def test_the_old_client_side_payload_is_what_produced_these(self):
		"""The defect, reproduced through the call the Approve button used to make.

		`frappe.client.set_value` with the decision alone is still a legal Frappe
		write — Desk's edit-then-submit relies on it — so the half-state remains
		*reachable*. What changed is that the approval UI no longer produces it,
		and anything left behind is now findable instead of silent.
		"""
		import frappe.client

		name = self.draft(13)
		frappe.set_user(APPROVER)
		frappe.client.set_value("Leave Application", name, {"status": "Approved"})

		self.assertEqual(
			state(name), {"docstatus": 0, "status": "Approved", "leave_approver": APPROVER, "ledger": 0}
		)
		frappe.set_user(HR_MANAGER)
		self.assertEqual(report_half_transitioned("Leave Application")["Leave Application"]["count"], 1)

		# and `decide` finishes it in one call, with one ledger effect
		frappe.set_user(APPROVER)
		decide("Leave Application", name, "Approved")
		self.assertEqual(
			state(name), {"docstatus": 1, "status": "Approved", "leave_approver": APPROVER, "ledger": 1}
		)

	def test_it_covers_every_decide_then_submit_doctype(self):
		frappe.set_user(HR_MANAGER)
		self.assertEqual(set(report_half_transitioned()), set(DECIDE_THEN_SUBMIT))

	def test_an_ordinary_employee_cannot_run_it(self):
		frappe.set_user(EMPLOYEE)
		with self.assertRaises(frappe.PermissionError):
			report_half_transitioned()
