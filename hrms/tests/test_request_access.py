"""The system finds who cannot file their own requests — nobody is asked.

`hrms.utils.request_access` walks every enabled User linked to an Active
Employee, asks Frappe as that user whether they may create each PWA request
doctype, and keeps the refusals. Pinned here, bench-free:

  * impersonating a user puts the request's session back EXACTLY — user,
    sid, data and form_dict — because `frappe.set_user` overwrites `sid` with
    the username and the response cookie is written from it;
  * linked users are grouped on the NORMALIZED login, disabled users are
    skipped, a login two Active Employees claim is reported as `identity`;
  * the walk keeps only refusals, with the gate and the sentence from
    hrms.api.diagnose, and probes as the user (impersonation per user);
  * the health-log lines, and the nightly heal that runs every known repair
    and isolates a failing one.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_request_access.py
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.utils import request_access as ra

HR = "hr@example.com"
ANN, BOB = "ann@example.com", "bob@example.com"


class _Local:
	"""The slice of frappe.local the impersonation touches, with a set_user
	that does what the real one does to it."""

	def __init__(self, user, sid):
		self.session = frappe._dict(user=user, sid=sid, data=frappe._dict(csrf="t"))
		self.form_dict = frappe._dict(cmd="report")

	def set_user(self, user):
		self.session.user = user
		self.session.sid = user
		self.session.data = frappe._dict()
		self.form_dict = frappe._dict()


class TestImpersonatingRestoresTheSession(unittest.TestCase):
	def test_user_sid_data_and_form_dict_come_back(self):
		local = _Local(HR, "real-sid")
		with (
			patch.object(frappe, "local", local),
			patch.object(frappe, "set_user", side_effect=local.set_user) as set_user,
		):
			with ra.impersonating(ANN):
				self.assertEqual(local.session.user, ANN)
			self.assertEqual(set_user.call_args_list, [call(ANN), call(HR)])
		self.assertEqual(local.session.user, HR)
		self.assertEqual(local.session.sid, "real-sid", "the cookie would be rewritten from a clobbered sid")
		self.assertEqual(local.session.data, {"csrf": "t"})
		self.assertEqual(local.form_dict, {"cmd": "report"})

	def test_restored_even_when_the_block_raises(self):
		local = _Local(HR, "real-sid")
		with (
			patch.object(frappe, "local", local),
			patch.object(frappe, "set_user", side_effect=local.set_user),
		):
			with self.assertRaises(RuntimeError):
				with ra.impersonating(ANN):
					raise RuntimeError("probe blew up")
		self.assertEqual((local.session.user, local.session.sid), (HR, "real-sid"))


def _employees(*rows):
	return [frappe._dict(r) for r in rows]


class TestLinkedUsers(unittest.TestCase):
	def _linked(self, employees, enabled, companies=None):
		def get_all(doctype, filters=None, fields=None, pluck=None, order_by=None, **kw):
			if doctype == "Employee":
				self.employee_filters = filters
				return employees
			return [u for u in enabled if u in filters["name"][1]]

		with patch.object(frappe, "get_all", side_effect=get_all):
			return ra.linked_users(companies)

	def test_groups_on_the_normalized_login_and_skips_disabled_users(self):
		users = self._linked(
			_employees(
				{"name": "E1", "employee_name": "Ann", "user_id": "  Ann@Example.com ", "company": "Co A"},
				{"name": "E2", "employee_name": "Bob", "user_id": BOB, "company": "Co A"},
				{"name": "E3", "employee_name": "Gone", "user_id": "gone@example.com", "company": "Co A"},
			),
			enabled=[ANN, BOB],
		)
		self.assertEqual([(u.user, u.employee) for u in users], [(ANN, "E1"), (BOB, "E2")])

	def test_two_active_claimants_are_reported_not_guessed(self):
		users = self._linked(
			_employees(
				{"name": "E1", "employee_name": "Ann", "user_id": ANN, "company": "Co A"},
				{"name": "E9", "employee_name": "Ann again", "user_id": "ANN@example.com", "company": "Co A"},
			),
			enabled=[ANN],
		)
		self.assertEqual(len(users), 1)
		self.assertIsNone(users[0].employee)
		self.assertEqual(users[0].ambiguous, ["E1", "E9"])

	def test_the_company_fence_reaches_the_employee_query(self):
		self._linked([], enabled=[], companies=["Co A"])
		self.assertEqual(self.employee_filters["company"], ("in", ["Co A"]))
		self.assertEqual(self.employee_filters["status"], "Active")


class TestScanKeepsOnlyRefusals(unittest.TestCase):
	def _scan(self, people, allowed, doctypes=("Attendance Request", "Employee Issue")):
		seen = []

		def create_allowed(doctype, user, employee, meta=None):
			seen.append((frappe.session.user, user, doctype))
			return allowed(user, doctype)

		local = _Local(HR, "real-sid")
		with (
			patch.object(frappe, "local", local),
			patch.object(frappe, "session", local.session),
			patch.object(frappe, "set_user", side_effect=local.set_user),
			patch.object(frappe, "get_meta", return_value=MagicMock()),
			patch.object(ra, "linked_users", return_value=[frappe._dict(p) for p in people]),
			patch.object(ra, "create_allowed", side_effect=create_allowed),
			patch.object(
				ra,
				"diagnose_for_user",
				side_effect=lambda dt, user, employee=None: {
					"refused_by": "role",
					"why": f"{user} lacks {dt}",
				},
			) as diagnose,
		):
			rows = ra.scan(None, doctypes)
		return rows, seen, diagnose, local

	def test_two_users_one_refused(self):
		people = [
			{"user": ANN, "employee": "E1", "employee_name": "Ann", "company": "Co A", "ambiguous": []},
			{"user": BOB, "employee": "E2", "employee_name": "Bob", "company": "Co A", "ambiguous": []},
		]
		rows, seen, diagnose, local = self._scan(
			people, allowed=lambda user, dt: not (user == BOB and dt == "Employee Issue")
		)
		self.assertEqual(len(rows), 1)
		self.assertEqual(
			rows[0],
			{
				"user": BOB,
				"employee": "E2",
				"employee_name": "Bob",
				"company": "Co A",
				"doctype": "Employee Issue",
				"refused_by": "role",
				"why": "bob@example.com lacks Employee Issue",
			},
		)
		# the gate walk ran only for the refusal, and every probe ran AS that user
		diagnose.assert_called_once_with("Employee Issue", BOB, employee="E2")
		self.assertTrue(all(session_user == user for session_user, user, _ in seen), seen)
		self.assertEqual(len(seen), 4)
		self.assertEqual((local.session.user, local.session.sid), (HR, "real-sid"))

	def test_an_ambiguous_login_is_one_identity_row_and_never_probed(self):
		people = [
			{
				"user": ANN,
				"employee": None,
				"employee_name": "Ann",
				"company": "Co A",
				"ambiguous": ["E1", "E9"],
			}
		]
		rows, seen, _, _ = self._scan(people, allowed=lambda *a: True)
		self.assertEqual(seen, [])
		self.assertEqual((rows[0]["refused_by"], rows[0]["doctype"]), ("identity", None))
		self.assertIn("E1, E9", rows[0]["why"])


class TestSummaryAndLines(unittest.TestCase):
	def test_summary_counts_people_and_top_gates(self):
		rows = [
			{"user": ANN, "refused_by": "role"},
			{"user": ANN, "refused_by": "role"},
			{"user": BOB, "refused_by": "user_permission"},
		]
		with patch.object(ra, "scan", return_value=rows):
			summary = ra.refusal_summary()
		self.assertEqual(summary, {"users": 2, "rows": 3, "top": [("role", 2), ("user_permission", 1)]})

	def test_lines_name_the_count_and_the_reasons(self):
		lines = ra.summary_lines({"users": 2, "rows": 3, "top": [("role", 2), ("user_permission", 1)]})
		self.assertEqual(lines[0], "Request access:")
		self.assertIn("2 users cannot file their own requests (3 refusals)", lines[1])
		self.assertIn("role: 2", lines[2])
		self.assertIn("user_permission: 1", lines[3])

	def test_healthy_and_absent_summaries(self):
		self.assertIn("every linked user can file", ra.summary_lines({"users": 0, "rows": 0, "top": []})[1])
		self.assertEqual(ra.summary_lines(None), [])


class TestHealKnownShapes(unittest.TestCase):
	def test_runs_every_healer_in_order_and_isolates_a_failure(self):
		ran = []

		def get_attr(path):
			if "normalize" in path:
				return MagicMock(side_effect=RuntimeError("boom"))
			return lambda: ran.append(path)

		with (
			patch.object(frappe, "get_attr", side_effect=get_attr),
			patch.object(frappe, "log_error") as log_error,
			patch.object(frappe, "get_traceback", return_value="tb"),
		):
			outcome = ra.heal_known_shapes()
		self.assertEqual(
			ran,
			[
				"hrms.patches.v16_0.restore_staff_create_on_pwa_requests.execute",
				"hrms.patches.v16_0.realign_self_employee_permission.execute",
			],
		)
		self.assertEqual(outcome["hrms.patches.v16_0.normalize_employee_user_ids"], "error: boom")
		self.assertEqual(outcome["hrms.patches.v16_0.realign_self_employee_permission"], "ok")
		log_error.assert_called_once()

	def test_the_three_known_shapes_are_the_healers(self):
		self.assertEqual(
			ra.HEALERS,
			(
				"hrms.patches.v16_0.restore_staff_create_on_pwa_requests",
				"hrms.patches.v16_0.normalize_employee_user_ids",
				"hrms.patches.v16_0.realign_self_employee_permission",
			),
		)


if __name__ == "__main__":
	unittest.main()
