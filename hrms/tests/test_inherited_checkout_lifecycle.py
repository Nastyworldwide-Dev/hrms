"""Real Frappe insert lifecycle, with in-memory database/persistence boundaries.

Run with the bench Python interpreter:
<bench>/env/bin/python hrms/tests/test_inherited_checkout_lifecycle.py
No site, Redis or DB connection. System-Python collection explicitly skips
this module when only the lightweight framework stub is available.
"""

import logging
import sys
import unittest
from contextlib import ExitStack
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
	import frappe
	from frappe.model.document import Document as FrameworkDocument
except ModuleNotFoundError as exc:
	if not exc.name or exc.name.split(".")[0] != "frappe":
		raise
	raise unittest.SkipTest("Real Frappe lifecycle required; run this suite with the bench Python.") from exc

# Reject both the generic MagicMock module stub and another test's Document seam
# before importing the application controller (which would cache that false base).
if not isinstance(FrameworkDocument, type) or FrameworkDocument.__module__ != "frappe.model.document":
	raise unittest.SkipTest("Real Frappe lifecycle required; stub-only interpreter, run with bench Python.")

from frappe.model.docstatus import DocStatus

from hrms.hr.doctype.remote_checkin_request.remote_checkin_request import (
	_INHERITED_CHECKOUT,
	RemoteCheckinRequest,
)
from hrms.overrides import employee_checkin_after_insert as producer


class TestInheritedCheckoutInsert(unittest.TestCase):
	def setUp(self):
		self.stack = ExitStack()
		self.addCleanup(self.stack.close)
		frappe.local.session = frappe._dict(user="employee@example.invalid")
		frappe.local.flags = frappe._dict(in_test=True, in_migrate=True)
		frappe.local.db = MagicMock()
		frappe.local.conf = frappe._dict()
		self.rows = {
			("Employee", "EMP-1"): frappe._dict(
				name="EMP-1", user_id="employee@example.invalid", status="Active"
			),
			("Employee Checkin", "IN-1"): frappe._dict(
				name="IN-1",
				employee="EMP-1",
				log_type="IN",
				time=datetime(2026, 9, 3, 9),
				remote_approval_status="Approved",
			),
			("Employee Checkin", "OUT-1"): frappe._dict(
				name="OUT-1",
				employee="EMP-1",
				log_type="OUT",
				time=datetime(2026, 9, 3, 20),
				requires_remote_approval=1,
				remote_approval_status="Pending",
			),
			("Remote Checkin Request", "PARENT-1"): frappe._dict(
				name="PARENT-1",
				checkin="IN-1",
				employee="EMP-1",
				log_type="IN",
				status="Approved",
				approver="approver@example.invalid",
			),
		}
		self.requests = []
		self.stack.enter_context(patch.object(frappe, "get_system_settings", return_value="UTC"))
		self.stack.enter_context(patch.object(frappe, "new_doc", side_effect=self.new_request))
		self.stack.enter_context(patch.object(frappe, "get_all", side_effect=self.get_all))
		self.stack.enter_context(patch.object(frappe.db, "get_value", side_effect=self.get_value))
		self.stack.enter_context(patch.object(frappe.db, "exists", return_value=False))
		self.stack.enter_context(patch.object(frappe.db, "set_value"))
		self.stack.enter_context(patch.object(frappe, "get_roles", return_value=["Employee"]))
		self.stack.enter_context(patch.object(frappe, "_", side_effect=lambda value, *a, **kw: value))
		self.stack.enter_context(patch.object(producer, "notify_approver"))
		self.stack.enter_context(
			patch.object(producer, "resolve_approver", return_value="approver@example.invalid")
		)
		# Throw keeps its exception contract; rendering needs a site and is outside this seam.
		self.stack.enter_context(
			patch.object(
				frappe,
				"throw",
				side_effect=lambda message, *a, **kw: (_ for _ in ()).throw(frappe.ValidationError(message)),
			)
		)
		self.stack.enter_context(patch("frappe.model.document.relink_mismatched_files"))
		logging.disable(logging.CRITICAL)
		self.addCleanup(logging.disable, logging.NOTSET)

	def matches(self, row, filters):
		items = filters.items() if isinstance(filters, dict) else ((f[0], f[1:]) for f in filters)
		for field, expected in items:
			actual = row.get(field)
			if isinstance(expected, (list, tuple)):
				op, value = expected
				if op == "<=" and not actual <= value:
					return False
				if op == "<" and not actual < value:
					return False
				if op == "!=" and (actual is None or actual == value):
					return False
				if op == "is" and value == "not set" and actual is not None:
					return False
				if op == "=" and actual != value:
					return False
			else:
				if actual != expected:
					return False
		return True

	def get_all(self, doctype, filters=None, **kwargs):
		rows = [r for (dt, _), r in self.rows.items() if dt == doctype and self.matches(r, filters or {})]
		if kwargs.get("or_filters"):
			rows = [r for r in rows if any(self.matches(r, [f]) for f in kwargs["or_filters"])]
		rows.sort(key=lambda r: (r.time or datetime.min, r.name), reverse=True)
		return rows[: kwargs.get("limit_page_length", 999)]

	def get_value(self, doctype, name, fields=None, as_dict=False, **kwargs):
		row = (
			self.rows.get((doctype, name))
			if isinstance(name, str)
			else next(iter(self.get_all(doctype, filters=name)), None)
		)
		if not row:
			return None
		if as_dict:
			return frappe._dict(row)
		return tuple(row.get(field) for field in fields) if isinstance(fields, list) else row.get(fields)

	def new_request(self, doctype="Remote Checkin Request"):
		doc = object.__new__(RemoteCheckinRequest)
		doc.__dict__.update(
			doctype=doctype,
			name="RCR-NEW",
			docstatus=DocStatus(0),
			flags=frappe._dict(),
			_table_fieldnames={},
			meta=frappe._dict(issingle=0, is_virtual=0),
			parent_request=None,
			approved_at=None,
		)
		# Keep Document.insert, check_if_latest, load_doc_before_save, is_new,
		# run_before_save_methods, has_value_changed and controller methods REAL.
		for name in (
			"_set_defaults",
			"set_user_and_timestamp",
			"set_docstatus",
			"_validate_links",
			"set_new_name",
			"set_parent_in_children",
			"validate_higher_perm_levels",
			"_validate",
			"reset_computed_child_tables",
			"run_post_save_methods",
			"reset_seen",
			"set_title_field",
		):
			setattr(doc, name, MagicMock())
		doc.get_all_children = lambda: []
		doc.run_method = lambda name, *a, **kw: (
			getattr(type(doc), name)(doc) if hasattr(type(doc), name) else None
		)
		doc.db_insert = MagicMock()
		self.requests.append(doc)
		return doc

	def create_checkout(self):
		out = frappe._dict(self.rows[("Employee Checkin", "OUT-1")])
		out.flags = frappe._dict()
		producer.create_remote_request_if_needed(out)
		return self.requests[-1]

	def test_employee_checkout_inherits_approval_through_real_insert(self):
		request = self.create_checkout()
		self.assertEqual((request.status, request.parent_request), ("Approved", "PARENT-1"))
		request.db_insert.assert_called_once()

	def test_overnight_checkout_inherits_only_its_own_in(self):
		self.rows[("Employee Checkin", "IN-1")].time = datetime(2026, 9, 3, 22)
		self.rows[("Employee Checkin", "OUT-1")].time = datetime(2026, 9, 4, 7)
		self.assertEqual(self.create_checkout().status, "Approved")

	def test_hr_recorded_checkout_preserves_existing_inheritance(self):
		frappe.local.session.user = "hr@example.invalid"
		with patch.object(frappe, "get_roles", return_value=["HR Manager"]):
			self.assertEqual(self.create_checkout().status, "Approved")

	def test_rejected_out_does_not_block_an_approved_open_session(self):
		self.rows[("Employee Checkin", "REJECTED-OUT")] = frappe._dict(
			name="REJECTED-OUT",
			employee="EMP-1",
			log_type="OUT",
			time=datetime(2026, 9, 3, 18),
			remote_approval_status="Rejected",
		)
		for user, roles in [
			("employee@example.invalid", ["Employee"]),
			("approver@example.invalid", ["Employee"]),
			("hr@example.invalid", ["HR Manager"]),
		]:
			with self.subTest(user=user), patch.object(frappe, "get_roles", return_value=roles):
				frappe.local.session.user = user
				request = self.create_checkout()
				self.assertEqual((request.status, request.parent_request), ("Approved", "PARENT-1"))
				request.db_insert.assert_called_once()

	def test_closed_or_new_unapproved_session_creates_pending_request(self):
		for log_type, status in [
			("OUT", "Approved"),
			("OUT", "Pending"),
			("OUT", None),
			("OUT", ""),
			("IN", "Pending"),
		]:
			with self.subTest(log_type=log_type, status=status):
				self.rows[("Employee Checkin", "INTERVENING")] = frappe._dict(
					name="INTERVENING",
					employee="EMP-1",
					log_type=log_type,
					time=datetime(2026, 9, 3, 18),
					remote_approval_status=status,
				)
				request = self.create_checkout()
				self.assertEqual((request.status, request.parent_request), ("Pending", None))
				request.db_insert.assert_called_once()

	def test_direct_employee_approved_creation_still_refused(self):
		for marker in (None, True, "verified", {"trusted": True}):
			with self.subTest(marker=marker):
				request = self.new_request()
				request.update(
					dict(
						self.rows[("Remote Checkin Request", "PARENT-1")],
						name="NEW",
						checkin="OUT-1",
						log_type="OUT",
						parent_request="PARENT-1",
						checkin_time=self.rows[("Employee Checkin", "OUT-1")].time,
					)
				)
				request.flags.ignore_permissions = True
				request.flags.inherited_checkout = marker
				with self.assertRaises(frappe.ValidationError):
					request.insert()
				request.db_insert.assert_not_called()

	def test_verified_marker_cannot_bless_changed_evidence(self):
		mutations = {
			"parent employee": (("Remote Checkin Request", "PARENT-1"), "employee", "OTHER"),
			"parent rejected": (("Remote Checkin Request", "PARENT-1"), "status", "Rejected"),
			"parent pending": (("Remote Checkin Request", "PARENT-1"), "status", "Pending"),
			"wrong parent IN": (("Remote Checkin Request", "PARENT-1"), "checkin", "OTHER-IN"),
			"rejected IN": (("Employee Checkin", "IN-1"), "remote_approval_status", "Rejected"),
			"OUT belongs to other employee": (("Employee Checkin", "OUT-1"), "employee", "OTHER"),
			"unowned OUT": (("Employee", "EMP-1"), "user_id", "other@example.invalid"),
		}
		for label, (key, field, value) in mutations.items():
			with self.subTest(label=label):
				original = self.rows[key][field]
				self.rows[key][field] = value
				request = self.new_request()
				request.update(
					dict(
						employee="EMP-1",
						checkin="OUT-1",
						log_type="OUT",
						status="Approved",
						parent_request="PARENT-1",
						approver="approver@example.invalid",
						checkin_time=datetime(2026, 9, 3, 20),
					)
				)
				request.flags.ignore_permissions = True
				request.flags.inherited_checkout = _INHERITED_CHECKOUT
				with self.assertRaises(frappe.ValidationError):
					request.insert()
				request.db_insert.assert_not_called()
				self.rows[key][field] = original

	def test_late_checkout_cannot_use_trusted_derivation(self):
		request = self.new_request()
		request.update(
			dict(
				employee="EMP-1",
				checkin="OUT-1",
				log_type="OUT",
				status="Approved",
				parent_request="PARENT-1",
				approver="approver@example.invalid",
				checkin_time=datetime(2026, 9, 3, 20),
				is_late_checkout=1,
			)
		)
		request.flags.ignore_permissions = True
		request.flags.inherited_checkout = _INHERITED_CHECKOUT
		with self.assertRaises(frappe.ValidationError):
			request.insert()
		request.db_insert.assert_not_called()

	def test_pending_creation_and_legitimate_approver_decision_still_insert(self):
		for user, status in [
			("employee@example.invalid", "Pending"),
			("approver@example.invalid", "Approved"),
		]:
			with self.subTest(status=status):
				frappe.local.session.user = user
				request = self.new_request()
				request.update(
					dict(
						employee="EMP-1", checkin="OUT-1", status=status, approver="approver@example.invalid"
					)
				)
				request.flags.ignore_permissions = True
				request.insert()
				request.db_insert.assert_called_once()

	def saved_request(self, old_status, status):
		request = self.new_request()
		request.update(
			dict(
				employee="EMP-1",
				checkin="OUT-1",
				log_type="OUT",
				status=status,
				approver="approver@example.invalid",
				approved_at=datetime(2026, 9, 3, 21),
			)
		)
		request.flags.ignore_permissions = True
		request._non_computed_table_fieldnames = {}
		request._original_modified = "2026-09-03 21:00:00"
		previous = frappe._dict(
			status=old_status, docstatus=DocStatus(0), modified=request._original_modified
		)
		self.stack.enter_context(patch.object(frappe, "get_doc", return_value=previous))
		for name in (
			"check_if_locked",
			"_restore_masked_fields_from_db",
			"set_name_in_children",
			"update_children",
		):
			setattr(request, name, MagicMock())
		request.db_update = MagicMock()
		return request

	def test_settled_decisions_cannot_be_reset_or_reversed_by_desk_save(self):
		for old_status in ("Approved", "Rejected"):
			for status in ("Pending", "Approved", "Rejected"):
				if status == old_status:
					continue
				with (
					self.subTest(old_status=old_status, status=status),
					patch.object(frappe, "get_roles", return_value=["HR Manager"]),
				):
					request = self.saved_request(old_status, status)
					with self.assertRaisesRegex(frappe.ValidationError, "already been decided"):
						request.save()
					request.db_update.assert_not_called()

	def test_pending_decisions_remain_authorized_through_real_save(self):
		for actor in ("employee@example.invalid", "approver@example.invalid"):
			for status in ("Approved", "Rejected"):
				with self.subTest(actor=actor, status=status):
					frappe.local.session.user = actor
					request = self.saved_request("Pending", status)
					if actor == "employee@example.invalid":
						with self.assertRaises(frappe.ValidationError):
							request.save()
						request.db_update.assert_not_called()
					else:
						request.save()
						request.db_update.assert_called_once()

	def test_settled_status_unchanged_still_allows_ordinary_save(self):
		for status in ("Approved", "Rejected"):
			with self.subTest(status=status):
				request = self.saved_request(status, status)
				request.approver_remarks = "Clarified explanation"
				request.save()
				request.db_update.assert_called_once()


if __name__ == "__main__":
	unittest.main()
