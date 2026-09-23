"""A decision is always recordable.

`decide()` sets the decision field and submits in ONE save, so every check
written for FILING runs again when the approver taps. Between filing and
decision the world moves: punches mark a day Present, an attachment rule is
switched on, the balance is spent elsewhere, the department approver table
changes. The 21 Sep Attendance Request fix
(test_attendance_request_decision_is_always_possible.py) drew the line for one
validator; this is the same line for the rest of the decide-then-submit family:

  * A REJECT never needs balance, evidence, attendance or an approver table —
    rejecting writes nothing. It always goes through.
  * An APPROVE keeps the checks that guard money and attendance: Leave with a
    Present day is still refused, naming the days; OT without the required
    attachment is still refused.

Bench-free: Leave and Shift methods are lifted from the controllers by AST
(their modules need a bench); the OT controller loads through the
test_ot_filing_edits stand-ins.

    PYTHONPATH=.:hrms/tests python3 hrms/tests/test_a_decision_is_always_recordable.py
"""

import ast
import importlib
import pathlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()

ROOT = pathlib.Path(__file__).resolve().parents[1]
LEAVE = ROOT / "hr/doctype/leave_application/leave_application.py"
SHIFT = ROOT / "hr/doctype/shift_request/shift_request.py"

PRESENT_DAYS = [
	{"name": "HR-ATT-1", "attendance_date": "2026-09-02"},
	{"name": "HR-ATT-2", "attendance_date": "2026-09-03"},
]


class _Refused(Exception):
	pass


class _Column:
	"""A pypika column stand-in: every comparison and combination is just a column."""

	def _same(self, *_):
		return self

	__le__ = __ge__ = __eq__ = __and__ = __or__ = __rand__ = __ror__ = _same
	__hash__ = object.__hash__


def _lift(path, cls_name, fn_name, **extra):
	tree = ast.parse(path.read_text())
	cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls_name)
	fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == fn_name)
	frappe = MagicMock()
	frappe.throw.side_effect = lambda msg, *a, **k: (_ for _ in ()).throw(_Refused(msg))
	frappe.bold = str
	ns = {
		"frappe": frappe,
		"_": lambda s: s,
		"logger": MagicMock(),
		"formatdate": str,
		"get_link_to_form": lambda dt, name, label=None: label or name,
		"AttendanceAlreadyMarkedError": _Refused,
		**extra,
	}
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), "exec"), ns)
	return ns[fn_name], frappe


def _leave(status):
	return SimpleNamespace(
		name="HR-LAP-SYNTHETIC",
		employee="EMP-SYNTHETIC",
		leave_type="Annual Leave",
		from_date="2026-09-02",
		to_date="2026-09-03",
		status=status,
	)


class TestLeaveWithPresentDays(unittest.TestCase):
	"""(a) Present attendance on the leave dates."""

	def _run(self, status):
		fn, frappe = _lift(LEAVE, "LeaveApplication", "validate_attendance")
		frappe.get_all.return_value = [SimpleNamespace(**d) for d in PRESENT_DAYS]
		fn(_leave(status))

	def test_filing_is_refused_naming_the_days(self):
		with self.assertRaises(_Refused) as ctx:
			self._run("Open")
		self.assertIn("2026-09-02", str(ctx.exception))

	def test_approve_is_still_refused_naming_the_days(self):
		with self.assertRaises(_Refused) as ctx:
			self._run("Approved")
		self.assertIn("2026-09-03", str(ctx.exception))

	def test_reject_goes_through(self):
		self._run("Rejected")


class TestLeaveWithSalaryProcessed(unittest.TestCase):
	"""(c) an LWP whose days a submitted Salary Slip already covers."""

	def _run(self, status):
		fn, frappe = _lift(LEAVE, "LeaveApplication", "validate_salary_processed_days", Order=MagicMock())
		frappe.db.get_value.return_value = 1  # is_lwp
		# The query builder is a MagicMock; its columns must survive `<=` against
		# plain dates for the query to be built. One covering slip comes back.
		frappe.qb.DocType.return_value = SimpleNamespace(
			start_date=_Column(), end_date=_Column(), docstatus=_Column(), employee=_Column(), creation=1
		)
		chain = frappe.qb.from_.return_value.select.return_value.where.return_value.orderby.return_value
		chain.limit.return_value.run.return_value = [("2026-09-01", "2026-09-30")]
		fn(_leave(status))

	def test_approve_is_refused(self):
		with self.assertRaises(_Refused):
			self._run("Approved")

	def test_reject_goes_through(self):
		self._run("Rejected")


class TestLeaveWithZeroBalance(unittest.TestCase):
	"""(c) zero balance — a rejection needs none."""

	def _run(self, status):
		fn, _frappe = _lift(
			LEAVE,
			"LeaveApplication",
			"validate_balance_leaves",
			cint=int,
			flt=lambda v, precision=None: float(v),
			get_number_of_leave_days=lambda *a, **k: 2.0,
			is_lwp=lambda lt: False,
			validate_leave_access=lambda employee: None,
			get_consumable_leave_balance=lambda *a, **k: 0.0,
		)
		doc = _leave(status)
		doc.half_day = 0
		doc.half_day_date = None
		doc.leave_balance = 0
		doc.show_insufficient_balance_message = MagicMock(side_effect=_Refused("Insufficient"))
		fn(doc)
		return doc

	def test_approve_is_refused(self):
		with self.assertRaises(_Refused):
			self._run("Approved")

	def test_reject_goes_through_and_still_counts_the_days(self):
		doc = self._run("Rejected")
		self.assertEqual(doc.total_leave_days, 2.0)


class TestShiftApproverTableChangedSinceFiling(unittest.TestCase):
	def _run(self, status, is_new=False, approver_changed=False):
		# validate_approver reads the employee's designated approvers (the chain,
		# 5134f4856) and words a refusal with no_approver_message (ab74a7904);
		# the lifted function needs both, or every filing case raised NameError
		# instead of the refusal it is testing.
		fn, _frappe = _lift(
			SHIFT,
			"ShiftRequest",
			"validate_approver",
			get_designated_approvers=lambda *a: ["old.approver@example.com"],
			no_approver_message=lambda approvers, picked: f"{picked} is not one of your approvers",
		)
		fn(
			SimpleNamespace(
				name="HR-SHR-SYNTHETIC",
				employee="EMP-SYNTHETIC",
				approver="named.approver@example.com",
				status=status,
				is_new=lambda: is_new,
				has_value_changed=lambda field: approver_changed and field == "approver",
			)
		)

	def test_filing_with_a_stranger_as_approver_is_refused(self):
		with self.assertRaises(_Refused):
			self._run("Draft")

	def test_reject_goes_through(self):
		self._run("Rejected")

	def test_approve_goes_through(self):
		self._run("Approved")

	def test_a_new_row_filed_already_decided_is_still_a_filing(self):
		# The status field is the filer's; a REST insert with status=Approved and a
		# stranger as approver must not switch the trust-boundary check off.
		with self.assertRaises(_Refused):
			self._run("Approved", is_new=True)

	def test_changing_the_approver_with_the_status_is_still_a_filing(self):
		with self.assertRaises(_Refused):
			self._run("Rejected", approver_changed=True)


class TestOTWithoutTheRequiredAttachment(unittest.TestCase):
	"""(b) missing attachment: the rule that would refuse it must not stop the refusal."""

	def _submit(self, status):
		filing = importlib.import_module("test_ot_filing_edits")
		ot_request = filing.ot_request
		doc = ot_request.OTRequest.__new__(ot_request.OTRequest)
		doc.__dict__.update(
			doctype="OT Request",
			name="OT-SYNTHETIC",
			employee="EMP-SYNTHETIC",
			status=status,
			compensation="Overtime Pay",
		)
		missing = MagicMock(side_effect=_Refused("A supporting attachment is required"))
		with (
			patch.object(ot_request, "validate_mandatory_attachment", missing),
			patch.object(ot_request.OTRequest, "notify_approval_status", MagicMock()),
		):
			doc.on_submit()

	def test_approve_is_refused_as_today(self):
		with self.assertRaises(_Refused):
			self._submit("Approved")

	def test_reject_goes_through(self):
		self._submit("Rejected")


if __name__ == "__main__":
	unittest.main()
