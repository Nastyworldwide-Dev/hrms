"""The employee can see, and is told, what happened to their OT / Replacement Leave request.

Two halves of one symptom — "I filed it, then nothing":

  * `get_ot_requests` / `get_replacement_leave_claims` returned no `status`, so the
    PWA list could not tell a REJECTED request (docstatus 1, status Rejected) from
    an approved one — both looked "submitted".
  * Neither controller called `notify_approval_status()`: `OTRequest` mixes in
    `PWANotificationsMixin` but never used that half, and the mixin's status map
    had no "OT Request" key (a KeyError had it ever been called). `ReplacementLeaveClaim`
    did not use the mixin at all — no approver ping on filing, no outcome ping.

Bench-free: the field lists and the status map are read from the AST; the
`on_submit` hooks run on bare controller instances with the mixin method patched.

    PYTHONPATH=. python3 hrms/tests/test_request_outcome_visible.py
"""

import ast
import importlib
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "api/__init__.py"
MIXIN = ROOT / "mixins/pwa_notifications.py"

filing = importlib.import_module("test_ot_filing_edits")
OTRequest = filing.ot_request.OTRequest


def _load_replacement_leave_claim():
	"""The controller with the same stand-ins test_ot_filing_edits gives OT Request."""
	helpers = types.ModuleType("hrms.hr.utils")
	for name in (
		"create_additional_leave_ledger_entry",
		"get_leave_period",
		"reverse_replacement_leave",
		"validate_active_employee",
		"validate_filing_for_self",
		"validate_mandatory_attachment",
		"validate_self_submission",
	):
		setattr(helpers, name, lambda *args, **kwargs: None)
	spec = importlib.util.spec_from_file_location(
		"rl_claim_under_test", ROOT / "hr/doctype/replacement_leave_claim/replacement_leave_claim.py"
	)
	module = importlib.util.module_from_spec(spec)
	with patch.dict(
		sys.modules,
		{
			"frappe.model.document": filing.model,
			"hrms.hr.utils": helpers,
			"hrms.hr.doctype.ot_request.ot_request": filing.ot_request,
		},
	):
		spec.loader.exec_module(module)
	return module


rl_claim = _load_replacement_leave_claim()
ReplacementLeaveClaim = rl_claim.ReplacementLeaveClaim


def _fn(path, name):
	tree = ast.parse(path.read_text())
	return next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)


def _field_list(func_name):
	"""The `fields=[...]` literal handed to frappe.get_list inside the reader."""
	for node in ast.walk(_fn(API, func_name)):
		if isinstance(node, ast.Call):
			for kw in node.keywords:
				if kw.arg == "fields" and isinstance(kw.value, ast.List):
					return [ast.literal_eval(el) for el in kw.value.elts]
	raise AssertionError(f"{func_name} passes no fields list")


class TestTheListCanTellRejectedFromApproved(unittest.TestCase):
	def test_ot_requests_carry_status(self):
		self.assertIn("status", _field_list("get_ot_requests"))

	def test_replacement_leave_claims_carry_status(self):
		self.assertIn("status", _field_list("get_replacement_leave_claims"))


class TestTheMixinKnowsBothDoctypes(unittest.TestCase):
	def test_status_field_map_has_both_keys(self):
		src = _fn(MIXIN, "_get_doc_status_field")
		mapping = next(
			ast.literal_eval(n.value)
			for n in ast.walk(src)
			if isinstance(n, ast.Assign) and n.targets[0].id == "APPROVAL_STATUS_FIELD"
		)
		self.assertEqual(mapping.get("OT Request"), "status")
		self.assertEqual(mapping.get("Replacement Leave Claim"), "status")


def _bare(cls, **values):
	doc = cls.__new__(cls)
	doc.__dict__.update(values)
	return doc


class TestOTRequestTellsTheEmployee(unittest.TestCase):
	def _submit(self, status):
		doc = _bare(
			OTRequest,
			doctype="OT Request",
			name="OT-SYNTHETIC",
			employee="EMP-SYNTHETIC",
			status=status,
			compensation="Overtime Pay",
		)
		with patch.object(OTRequest, "notify_approval_status", MagicMock()) as told:
			doc.on_submit()
		return told

	def test_approval_is_notified(self):
		self.assertTrue(self._submit("Approved").called)

	def test_rejection_is_notified(self):
		self.assertTrue(self._submit("Rejected").called)


class TestReplacementLeaveClaimTellsTheEmployee(unittest.TestCase):
	def test_it_uses_the_mixin(self):
		# By name: the loader above re-imports the mixin module per controller, so
		# an identity check would compare two copies of the same class.
		self.assertIn(
			("PWANotificationsMixin", "hrms.mixins.pwa_notifications"),
			[(c.__name__, c.__module__) for c in ReplacementLeaveClaim.__mro__],
		)

	def test_filing_pings_the_approver_once_on_insert(self):
		doc = _bare(ReplacementLeaveClaim, doctype="Replacement Leave Claim", employee="EMP-SYNTHETIC")
		with patch.object(ReplacementLeaveClaim, "notify_approver", MagicMock(), create=True) as told:
			doc.after_insert()
		self.assertTrue(told.called)

	def _submit(self, status):
		doc = _bare(
			ReplacementLeaveClaim,
			doctype="Replacement Leave Claim",
			name="RLC-SYNTHETIC",
			employee="EMP-SYNTHETIC",
			status=status,
		)
		with (
			patch.object(ReplacementLeaveClaim, "add_to_leave_allocation", MagicMock()),
			patch.object(ReplacementLeaveClaim, "notify_approval_status", MagicMock(), create=True) as told,
		):
			doc.on_submit()
		return told

	def test_approval_is_notified(self):
		self.assertTrue(self._submit("Approved").called)

	def test_rejection_is_notified(self):
		self.assertTrue(self._submit("Rejected").called)


if __name__ == "__main__":
	unittest.main()
