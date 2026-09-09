"""OT Request and Replacement Leave Claim always carry the Employee's company.

The PWA create form does not send `company`, so a request's company was
whatever the user's default Company happened to be — right by luck for a
single-company user, blank or wrong otherwise — and every company-dependent
check downstream (leave period, company fence, grant) read that value.
`validate()` now derives it from the Employee, the way `set_compensation`
derives the compensation, before any company-dependent step.

Bench-free: bare controller instances, every other validate step patched out.

    PYTHONPATH=. python3 hrms/tests/test_request_company_from_employee.py
"""

import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()

filing = importlib.import_module("test_ot_filing_edits")
outcome = importlib.import_module("test_request_outcome_visible")
OTRequest = filing.ot_request.OTRequest
ReplacementLeaveClaim = outcome.ReplacementLeaveClaim

EMPLOYEE = "EMP-SYNTHETIC"
COMPANY = "CO-SYNTHETIC"


def _employee_company(doctype, name, fieldname=None, *args, **kwargs):
	if (doctype, name, fieldname) == ("Employee", EMPLOYEE, "company"):
		return COMPANY
	return None


class TestCompanyComesFromTheEmployee(unittest.TestCase):
	def test_ot_request(self):
		doc = OTRequest.__new__(OTRequest)
		doc.__dict__.update(doctype="OT Request", employee=EMPLOYEE, _new=True, _previous=None)
		with (
			patch.object(filing.ot_request.frappe.db, "get_value", side_effect=_employee_company),
			patch.object(OTRequest, "validate_filing_window", MagicMock()),
			patch.object(OTRequest, "set_compensation", MagicMock()),
			patch.object(OTRequest, "set_punch_verified_cap", MagicMock()),
			patch.object(OTRequest, "validate_claimed_hours", MagicMock()),
			patch.object(OTRequest, "validate_duplicate_request", MagicMock()),
		):
			doc.validate()
		self.assertEqual(getattr(doc, "company", None), COMPANY)

	def test_replacement_leave_claim(self):
		doc = ReplacementLeaveClaim.__new__(ReplacementLeaveClaim)
		doc.__dict__.update(doctype="Replacement Leave Claim", employee=EMPLOYEE, _new=True)
		with (
			patch.object(outcome.rl_claim.frappe.db, "get_value", side_effect=_employee_company),
			patch.object(ReplacementLeaveClaim, "set_claim_basis", MagicMock()),
			patch.object(ReplacementLeaveClaim, "validate_claimed_days", MagicMock()),
		):
			doc.validate()
		self.assertEqual(getattr(doc, "company", None), COMPANY)


if __name__ == "__main__":
	unittest.main()
