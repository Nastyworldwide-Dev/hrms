"""Local rollback-only storage and native submission regression, no DDL/commit.

Unrelated identity/link/filing checks are explicit synthetic boundaries. The
native Document submission and actual claimed-hours validator remain active.
"""

import sys
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import frappe

frappe.init(site="fresh.local", sites_path="/home/nabil/verify-bench/sites")
frappe.connect()
frappe.set_user("Administrator")
try:
	from hrms.hr.doctype.ot_request import ot_request as controller

	for minutes in (194, 1):
		hours = minutes / 60
		name = "SYNTHETIC-PRECISION-" + uuid4().hex[:12]
		doc = frappe.new_doc("OT Request")
		doc.claimed_hours = doc.punch_ot_hours = hours
		serialized = doc.get_valid_dict()["claimed_hours"]
		frappe.db.sql(
			"INSERT INTO `tabOT Request` (name,claimed_hours,punch_ot_hours) VALUES (%s,%s,%s)",
			(name, serialized, serialized),
		)
		doc = frappe.get_doc("OT Request", name)
		print({"minutes": minutes, "serialized": serialized, "reloaded": doc.claimed_hours})
		if minutes != 1:
			continue
		doc.status = "Approved"
		doc.flags.ignore_permissions = True
		with (
			patch.object(controller, "validate_active_employee"),
			patch.object(controller, "validate_filing_for_self"),
			patch.object(doc, "validate_filing_window"),
			patch.object(doc, "set_compensation"),
			patch.object(doc, "validate_duplicate_request"),
			patch.object(doc, "_validate_links"),
			patch.object(
				doc, "set_punch_verified_cap", side_effect=lambda: setattr(doc, "punch_ot_hours", hours)
			),
		):
			try:
				doc.submit()
			except frappe.ValidationError as error:
				assert "Cannot claim" in str(error), str(error)
				print("RED: native submit rejects the reloaded one-minute claim after decimal(21,2) storage")
			else:
				raise AssertionError("Expected existing precision loss to block this native submit")
finally:
	frappe.db.rollback()
	frappe.destroy()
