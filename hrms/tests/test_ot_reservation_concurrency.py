"""Opt-in real-database proof: two approvals for one employee serialize.

Astra's probe (docs/glass/audit/2026-09-08-ot-concurrency-probe.py) showed two
transactions each admitting 3 h against a 4 h monthly cap. This suite drives
the REAL approval endpoint from two threads, each with its own Frappe context
and database connection, on a local site with owned synthetic fixtures:

  * thread 1 approves its request and is held INSIDE the employee lock
    (after its capacity read, before commit);
  * thread 2 starts its approval, must block on the employee row, and only
    proceeds once thread 1 has committed;
  * thread 2's locking reservation read then sees thread 1's 3 h, its
    capacity is 1 h, and its 3 h claim is refused.

Also checks that the locking read uses the composite index the v16_0 patch
adds. Fixtures are synthetic, uniquely named and deleted afterwards.

From the bench sites directory:
  NADI_OT_TEST_SITE=fresh.local <bench>/env/bin/python <app>/hrms/tests/test_ot_reservation_concurrency.py
"""

import os
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
	import frappe
	from frappe.model.document import Document
except ModuleNotFoundError as exc:
	raise unittest.SkipTest("Real Frappe and NADI_OT_TEST_SITE required") from exc
if not isinstance(Document, type) or Document.__module__ != "frappe.model.document":
	raise unittest.SkipTest("Real Frappe required; the stub cannot test row locks")
SITE = os.environ.get("NADI_OT_TEST_SITE")
if not SITE:
	raise unittest.SkipTest("Set NADI_OT_TEST_SITE to an explicitly authorized local test site")

from hrms.api import approval
from hrms.hr.doctype.ot_request import ot_request as controller
from hrms.patches.v16_0 import add_ot_request_reservation_index as index_patch
from hrms.utils import ot_calculation as ot

TAG = uuid4().hex[:10]
COMPANY = f"SYN-CO-{TAG}"
EMPLOYEE = f"SYN-EMP-{TAG}"
SHIFT = f"SYN-SHIFT-{TAG}"
DATES = ("2026-09-01", "2026-09-02")
CAP = 4.0
ENTITLEMENT = 3.0


def _entitlement(employee, start, end, basic, default, approved=None, **kwargs):
	"""A fixed 3 h weekday entitlement under a 4 h monthly cap, any day."""
	from frappe.utils import getdate

	day = getdate(start)
	hours = ENTITLEMENT if approved is None else min(ENTITLEMENT, approved.get(day, 0))
	if hours <= 0:
		return iter([])
	return iter(
		[
			{
				"day": day,
				"monthly_cap": CAP,
				"unrounded_ot_hours": hours,
				"ot_hours": hours,
				"normal_hours": hours,
				"nonworking_hours": 0.0,
				"day_type": "normal",
				"hourly_rate": 10.0,
				"bands": [{"day_type": "normal", "rate": 1.5, "hours": hours, "amount": hours * 15}],
				"amount": hours * 15,
				"contributions": [{"shift": SHIFT, "day_type": "normal", "hours": hours}],
			}
		]
	)


class TestTwoApprovalsSerializeOnTheEmployee(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		frappe.init(site=SITE)
		frappe.connect()
		frappe.set_user("Administrator")
		index_patch.execute()  # authorized LOCAL index; idempotent
		frappe.db.sql(
			"INSERT INTO `tabCompany` (name, abbr, country, default_currency) VALUES (%s, %s, %s, %s)",
			(COMPANY, "SYN", "Malaysia", "MYR"),
		)
		frappe.db.sql(
			"INSERT INTO `tabEmployee` (name, employee_name, company, status, date_of_joining, "
			"eligible_for_overtime_pay) VALUES (%s, %s, %s, %s, %s, 1)",
			(EMPLOYEE, "Synthetic", COMPANY, "Active", "2026-01-01"),
		)
		frappe.get_doc(
			{"doctype": "Shift Type", "name": SHIFT, "start_time": "09:00:00", "end_time": "18:00:00"}
		).db_insert()
		cls.names = []
		with (
			patch.object(ot, "_iter_day_ot", side_effect=_entitlement),
			patch.object(controller.OTRequest, "after_insert", lambda self: None),
		):
			for day in DATES:
				doc = frappe.get_doc(
					{
						"doctype": "OT Request",
						"employee": EMPLOYEE,
						"company": COMPANY,
						"employee_name": "Synthetic",
						"shift": SHIFT,
						"ot_date": day,
						"status": "Open",
						"claimed_hours": ENTITLEMENT,
						"explanation": "Synthetic concurrency verification",
					}
				)
				doc.insert()
				cls.names.append(doc.name)
		frappe.db.commit()  # owned synthetic fixtures only

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		for name in cls.names:
			frappe.db.delete("OT Request", {"name": name})
		frappe.db.delete("Employee", {"name": EMPLOYEE})
		frappe.db.delete("Shift Type", {"name": SHIFT})
		frappe.db.delete("Company", {"name": COMPANY})
		frappe.db.commit()
		for doctype, name in (("OT Request", cls.names[0]), ("Employee", EMPLOYEE), ("Company", COMPANY)):
			assert not frappe.db.exists(doctype, name), f"Synthetic {doctype} cleanup failed"
		frappe.destroy()

	def test_the_locking_read_uses_the_composite_index(self):
		plan = frappe.db.sql(
			"EXPLAIN SELECT name FROM `tabOT Request` WHERE employee=%s AND docstatus=1 "
			"AND ot_date BETWEEN %s AND %s FOR UPDATE",
			(EMPLOYEE, "2026-09-01", "2026-09-30"),
			as_dict=True,
		)
		self.assertEqual(plan[0]["key"], index_patch.INDEX_NAME, plan)

	def test_the_second_approval_waits_and_is_refused(self):
		inside = threading.Event()
		release = threading.Event()
		outcomes = {}
		original_cap = controller.OTRequest.set_punch_verified_cap

		def held_cap(doc):
			original_cap(doc)
			if getattr(frappe.local, "synthetic_hold", False):
				inside.set()
				release.wait(timeout=30)

		def approve(index, hold):
			frappe.init(site=SITE)
			frappe.connect()
			frappe.set_user("Administrator")
			frappe.local.synthetic_hold = hold
			try:
				approval.decide("OT Request", self.names[index], "Approved")
				frappe.db.commit()
				outcomes[index] = ("approved", time.monotonic())
			except Exception as exc:  # the refusal is the expected outcome for the loser
				frappe.db.rollback()
				outcomes[index] = (str(exc), time.monotonic())
			finally:
				frappe.destroy()

		with (
			patch.object(ot, "_iter_day_ot", side_effect=_entitlement),
			patch.object(controller.OTRequest, "set_punch_verified_cap", held_cap),
		):
			first = threading.Thread(target=approve, args=(0, True))
			second = threading.Thread(target=approve, args=(1, False))
			first.start()
			self.assertTrue(inside.wait(timeout=30), "thread 1 never reached the held section")
			second.start()
			time.sleep(1.5)  # thread 2 must be blocked on the employee row by now
			self.assertNotIn(1, outcomes, "thread 2 proceeded while thread 1 held the employee lock")
			released_at = time.monotonic()
			release.set()
			first.join(timeout=60)
			second.join(timeout=60)

		self.assertEqual(outcomes[0][0], "approved", outcomes)
		self.assertIn("at most", outcomes[1][0], outcomes)
		self.assertGreater(outcomes[1][1], released_at)
		frappe.db.rollback()
		submitted = frappe.db.get_values(
			"OT Request", {"employee": EMPLOYEE, "docstatus": 1}, ["name", "claimed_hours"], as_dict=True
		)
		self.assertEqual([row.name for row in submitted], [self.names[0]])
		self.assertLessEqual(sum(row.claimed_hours for row in submitted), CAP)


if __name__ == "__main__":
	unittest.main()
