"""Local verification only: two real transactions, synthetic rows, rollback always.

Run with verify-bench Python, cwd verify-bench/sites. No commit or DDL.
The real claim-capacity function runs; punch-derived daily entitlement is a
fixed boundary so this probe isolates reservation transactions.
"""

import sys
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import frappe

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from hrms.utils import ot_calculation as ot

assert Path(ot.__file__).resolve() == REPO / "hrms/utils/ot_calculation.py"
frappe.init(site="fresh.local", sites_path="/home/nabil/verify-bench/sites")
frappe.connect()
connections = []
try:
	for _ in range(2):
		connection = frappe.db.create_connection()
		connection.begin()
		connections.append(connection)
	identifier = "SYNTHETIC-OT-" + uuid4().hex[:12]
	capacities = []
	for index, connection in enumerate(connections):
		with connection.cursor() as cursor:
			cursor.execute("SELECT @@tx_isolation")
			assert cursor.fetchone()[0] == "REPEATABLE-READ"
			cursor.execute(
				"INSERT INTO `tabOT Request` (name, employee, ot_date, claimed_hours, compensation, status, docstatus) "
				"VALUES (%s, %s, %s, 3, 'Overtime Pay', 'Open', 0)",
				(identifier + str(index), identifier, f"2026-09-{18 + index}"),
			)
	for index, connection in enumerate(connections):

		def reservations(doctype, filters, fields):
			assert doctype == "OT Request"
			assert filters["docstatus"] == 1 and filters["status"] == ("!=", "Rejected")
			with connection.cursor() as cursor:
				cursor.execute(
					"SELECT claimed_hours FROM `tabOT Request` WHERE employee=%s AND docstatus=1 "
					"AND status!='Rejected' AND compensation='Overtime Pay' AND ot_date BETWEEN %s AND %s",
					(identifier, *filters["ot_date"][1]),
				)
				return [frappe._dict(claimed_hours=row[0]) for row in cursor.fetchall()]

		with (
			patch.object(ot, "_iter_day_ot", return_value=iter([{"ot_hours": 3, "monthly_cap": 4}])),
			patch.object(frappe, "get_all", side_effect=reservations),
		):
			capacity = ot.get_ot_claim_capacity(identifier, f"2026-09-{18 + index}", "Overtime Pay")["hours"]
		capacities.append(capacity)
		with connection.cursor() as cursor:
			cursor.execute(
				"UPDATE `tabOT Request` SET status='Approved', docstatus=1 WHERE name=%s",
				(identifier + str(index),),
			)
	print({"isolated_transactions": 2, "capacities": capacities, "monthly_cap": 4, "rolled_back": True})
	assert sum(capacities) <= 4, "Both transactions admitted 3h against one 4h monthly allowance"
finally:
	for connection in connections:
		connection.rollback()
		connection.close()
	frappe.db.rollback()
	frappe.destroy()
