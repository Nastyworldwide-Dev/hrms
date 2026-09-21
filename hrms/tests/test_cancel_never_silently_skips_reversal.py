"""A cancel never silently skips the reversal.

`reverse_replacement_leave` runs inside the CANCEL of an approved OT Request
or Replacement Leave Claim. It used to `log_error` and return when the
allocation was missing or not submitted, and to clamp to the unused days with
a msgprint when some were already taken — the cancel went through, `finalize`
reported success, and nobody read the Error Log.

Rules (succeeds test_rl_reversal_survives_a_missing_allocation.py, whose
"the withdrawal must go through" half still holds):

  * Days ALREADY TAKEN cannot be un-taken. That reversal is impossible, so
    the cancel is REFUSED with a plain sentence and nothing is written.
  * A MISSING or unsubmitted allocation (HR cancelled it, or the sync re-pulled
    the mirror under a new name — nothing HR can repair from Desk) does not
    block the withdrawal. The reversal is skipped VISIBLY: a sentence comes
    back, OTRequest.on_cancel puts it on the request's timeline and in
    `flags.reversal_note`, and `finalize` returns it as `reversal`.

Bench-free: the function is lifted from hrms/hr/utils.py by AST; the OT
controller loads through the test_ot_filing_edits stand-ins.

    PYTHONPATH=.:hrms/tests python3 hrms/tests/test_cancel_never_silently_skips_reversal.py
"""

import ast
import datetime
import importlib
import pathlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()

UTILS = pathlib.Path(__file__).resolve().parents[1] / "hr/utils.py"


class _Refused(Exception):
	pass


class _dict(dict):
	"""frappe._dict: keys are attributes (doc.flags is one)."""

	def __getattr__(self, key):
		return self.get(key)

	def __setattr__(self, key, value):
		self[key] = value


def _allocation(docstatus=1, total=1.0):
	return SimpleNamespace(
		name="HR-LAL-SYNTHETIC",
		docstatus=docstatus,
		employee="EMP-SYNTHETIC",
		leave_type="Replacement Leave",
		from_date=datetime.date(2026, 9, 2),
		to_date=datetime.date(2026, 12, 31),
		new_leaves_allocated=total,
		total_leaves_allocated=total,
		db_set=MagicMock(),
		add_comment=MagicMock(),
	)


def _reverse(*, allocation, taken=0.0):
	"""Run reverse_replacement_leave against one allocation state; return the mocks."""
	tree = ast.parse(UTILS.read_text())
	fn = next(
		n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "reverse_replacement_leave"
	)
	frappe = MagicMock()
	frappe.db.exists.return_value = allocation is not None
	frappe.get_doc.return_value = allocation
	frappe.throw.side_effect = lambda msg, *a, **k: (_ for _ in ()).throw(_Refused(msg))
	frappe.bold = str
	ledger = MagicMock()
	ns = {
		"frappe": frappe,
		"_": lambda s: s,
		"logger": MagicMock(),
		"flt": float,
		"cint": int,
		"getdate": lambda v=None: v or datetime.date(2026, 10, 1),
		"create_additional_leave_ledger_entry": ledger,
		"_reversible_days": lambda total, taken, requested: min(requested, max(0.0, total - taken)),
	}
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(UTILS), "exec"), ns)
	leave_app = MagicMock()
	leave_app.get_approved_leaves_for_period.return_value = taken
	with patch.dict(sys.modules, {"hrms.hr.doctype.leave_application.leave_application": leave_app}):
		note = ns["reverse_replacement_leave"]("HR-LAL-SYNTHETIC", 1.0)
	return frappe, ledger, note


class TestDaysAlreadyTakenRefuseTheCancel(unittest.TestCase):
	def test_refused_with_the_reason_and_nothing_written(self):
		allocation = _allocation(total=1.0)
		with self.assertRaises(_Refused) as ctx:
			_reverse(allocation=allocation, taken=1.0)
		self.assertIn("already taken", str(ctx.exception))
		allocation.db_set.assert_not_called()
		allocation.add_comment.assert_not_called()

	def test_no_clamp_and_no_error_log(self):
		"""No log_error-and-continue, no msgprint-and-clamp: the answer is the report."""
		fn = next(
			n
			for n in ast.parse(UTILS.read_text()).body
			if isinstance(n, ast.FunctionDef) and n.name == "reverse_replacement_leave"
		)
		called = {
			n.func.attr for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
		}
		self.assertFalse({"log_error", "msgprint"} & called, called)


class TestAMissingAllocationSkipsVisibly(unittest.TestCase):
	def test_missing_allocation_returns_the_note_and_does_not_throw(self):
		frappe, ledger, note = _reverse(allocation=None)
		frappe.throw.assert_not_called()
		ledger.assert_not_called()
		self.assertIn("HR-LAL-SYNTHETIC", note)
		self.assertIn("missing", note)

	def test_cancelled_allocation_returns_the_note_and_writes_nothing(self):
		allocation = _allocation(docstatus=2)
		frappe, _ledger, note = _reverse(allocation=allocation)
		frappe.throw.assert_not_called()
		allocation.db_set.assert_not_called()
		self.assertIn("not submitted", note)

	def test_a_full_reversal_returns_no_note(self):
		_frappe, _ledger, note = _reverse(allocation=_allocation(total=1.0))
		self.assertIsNone(note)

	def _cancel_ot(self, note):
		ot_request = importlib.import_module("test_ot_filing_edits").ot_request
		doc = ot_request.OTRequest.__new__(ot_request.OTRequest)
		doc.__dict__.update(
			doctype="OT Request",
			name="OT-SYNTHETIC",
			compensation=ot_request.REPLACEMENT_LEAVE,
			leave_allocation="HR-LAL-SYNTHETIC",
			leave_days_granted=1.0,
			flags=_dict(),
			add_comment=MagicMock(),
		)
		with patch.object(ot_request, "reverse_replacement_leave", return_value=note):
			doc.on_cancel()
		return doc

	def test_the_ot_cancel_puts_the_note_on_the_timeline_and_in_its_flags(self):
		doc = self._cancel_ot("No allocation to reverse: 1.0 day(s) … (HR-LAL-SYNTHETIC missing).")
		doc.add_comment.assert_called_once_with("Comment", doc.flags.reversal_note)
		self.assertIn("HR-LAL-SYNTHETIC", doc.flags.reversal_note)

	def test_a_full_reversal_leaves_no_comment(self):
		doc = self._cancel_ot(None)
		doc.add_comment.assert_not_called()
		self.assertFalse(doc.flags.get("reversal_note"))

	def _cancel_rl_claim(self, note):
		from hrms.hr.doctype.replacement_leave_claim import replacement_leave_claim as module

		doc = module.ReplacementLeaveClaim.__new__(module.ReplacementLeaveClaim)
		doc.__dict__.update(
			doctype="Replacement Leave Claim",
			name="RLC-SYNTHETIC",
			employee="EMP-SYNTHETIC",
			leave_allocation="HR-LAL-SYNTHETIC",
			claimed_days=1.0,
			flags=_dict(),
			add_comment=MagicMock(),
		)
		with patch("hrms.hr.utils.reverse_replacement_leave", return_value=note):
			doc.on_cancel()
		return doc

	def test_the_rl_claim_cancel_surfaces_the_note_the_same_way(self):
		# The second caller of the shared reverse dropped the note (verifier, 21 Sep).
		doc = self._cancel_rl_claim("No allocation to reverse: 1.0 day(s) … (HR-LAL-SYNTHETIC missing).")
		doc.add_comment.assert_called_once_with("Comment", doc.flags.reversal_note)

	def test_a_full_rl_claim_reversal_leaves_no_comment(self):
		doc = self._cancel_rl_claim(None)
		doc.add_comment.assert_not_called()

	def test_finalize_answers_with_the_note(self):
		from hrms.api import approval

		doc = _dict(doctype="OT Request", name="OT-SYNTHETIC", docstatus=2, status="Approved", flags=_dict())
		self.assertNotIn("reversal", approval._state(doc))
		doc.flags.reversal_note = "No allocation to reverse (HR-LAL-SYNTHETIC missing)."
		self.assertEqual(approval._state(doc)["reversal"], doc.flags.reversal_note)


class TestAHealthyAllocationIsReversedInFull(unittest.TestCase):
	def test_the_whole_grant_comes_back(self):
		allocation = _allocation(total=1.5)
		frappe, ledger, _note = _reverse(allocation=allocation, taken=0.5)
		frappe.throw.assert_not_called()
		allocation.db_set.assert_any_call("total_leaves_allocated", 0.5)
		ledger.assert_called_once()
		self.assertEqual(ledger.call_args.args[1], -1.0)


if __name__ == "__main__":
	unittest.main()
