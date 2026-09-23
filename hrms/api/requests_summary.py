# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""The numbers that belong where a request is STARTED (revamp §5).

Nielsen's sixth heuristic, recognition over recall: a person must not have to
hold a number in their head between two screens. Today the leave balance lives
on the leave dashboard and the decision to take leave is made on the form, so
an employee checks one screen, memorises a figure, and goes to another — and
the ones who do not bother are the ones who file a request that gets rejected.

NOTHING HERE IS NEW ARITHMETIC. Every figure already exists behind an endpoint
this app ships: `get_leave_balance_map`, `get_claimable_ot_summary`,
`get_expense_claims`. This composes them into one call so the Requests screen
makes one round trip instead of four, and — the part that matters — so the
numbers cannot disagree with the screens they came from. A second
implementation of "how much leave is left" is a second answer.

Session-scoped by construction: no endpoint takes an employee.
"""

import logging

import frappe
from frappe.utils import flt, getdate, nowdate

logger = logging.getLogger(__name__)

#: A balance worth stating. A leave type the employee has no allocation for is
#: not "0 days left" — it is not theirs, and listing it as a zero is how a
#: strip of five useful numbers becomes a wall of twelve.
MIN_ALLOCATION = 0.01

#: Expiry is only news while it is close enough to act on. A balance expiring
#: in nine months is a fact; one expiring in three weeks is a prompt.
EXPIRY_HORIZON_DAYS = 45


def _leave() -> list[dict]:
	"""Per type: what is left, out of what, and whether it is about to expire.

	Read through the app's own balance map rather than the allocation table,
	because that map resolves the ANNUAL ENTITLEMENT through three fallbacks
	(service slab, leave policy, then the allocation itself) and getting that
	denominator wrong is what makes a bar read 5 of 5 when it is 5 of 14.
	"""
	from hrms.api import get_current_employee, get_leave_balance_map
	from hrms.utils.timezone import employee_now

	# The employee's own day (rule 66a5e6145): an expiry countdown read off
	# the server clock was a day out near midnight in another time zone.
	employee = get_current_employee()
	today = employee_now(employee).date()

	# The balance map carries `from_date` and NOT `to_date` — verified on the
	# bench, after the first version of this read a key that is never there and
	# quietly reported nothing as expiring, ever. The end date comes from the
	# allocation itself, which is where it lives.
	expiry = {}
	if employee:
		for row in frappe.get_all(
			"Leave Allocation",
			filters={
				"employee": employee,
				"docstatus": 1,
				"to_date": (">=", today),
			},
			fields=["leave_type", "to_date"],
			order_by="to_date asc",
			ignore_permissions=True,
		):
			# Earliest end date wins: two allocations of one type mean the
			# nearer expiry is the one somebody has to act on.
			expiry.setdefault(row.leave_type, row.to_date)

	rows = []
	for leave_type, entry in (get_leave_balance_map() or {}).items():
		allocated = flt(entry.get("allocated_leaves"))
		if allocated < MIN_ALLOCATION:
			continue
		balance = flt(entry.get("balance_leaves"))
		expires = expiry.get(leave_type)
		days_left = (getdate(expires) - today).days if expires else None
		rows.append(
			{
				"leave_type": leave_type,
				"balance": balance,
				# The denominator is the ANNUAL entitlement, not what happens to
				# be allocated right now: a mid-year joiner with 7 of 14 has
				# used none of it, and "7 of 7" would say the opposite.
				"total": flt(entry.get("annual_entitlement")) or allocated,
				"expires_on": str(expires) if expires else None,
				# Only when it is close enough to be a prompt rather than a fact.
				"expiring_soon": bool(
					days_left is not None and 0 <= days_left <= EXPIRY_HORIZON_DAYS and balance > 0
				),
			}
		)
	rows.sort(key=lambda row: (-row["balance"], row["leave_type"]))
	return rows


def _overtime() -> dict:
	"""Worked and not yet claimed, and approved but not yet paid.

	Two different things an employee thinks of as "my overtime", and conflating
	them is how somebody believes they have been paid for a day they never
	filed.
	"""
	from hrms.api import get_claimable_ot_summary

	summary = get_claimable_ot_summary() or {}
	return {
		"unclaimed_days": len(summary.get("days") or []),
		"unclaimed_hours": flt(summary.get("claimable_hours")),
		# Which the claim becomes: pay, or a day off. The employee's own word
		# for it is decided on the screen; the wire value is carried as-is.
		"compensation": summary.get("compensation"),
	}


def _expenses() -> dict:
	"""Money out of pocket, in the two states that matter to the person who
	spent it: waiting for a decision, and decided but not yet paid."""
	from hrms.api import get_expense_claims

	claims = get_expense_claims() or []
	awaiting = sum(
		flt(claim.get("total_claimed_amount"))
		for claim in claims
		if (claim.get("approval_status") or "") == "Draft"
	)
	unpaid = sum(
		flt(claim.get("total_claimed_amount"))
		for claim in claims
		if (claim.get("approval_status") or "") == "Approved"
		and (claim.get("status") or "") in ("Unpaid", "Submitted")
	)
	currency = next((claim.get("currency") for claim in claims if claim.get("currency")), None)
	return {
		"awaiting_amount": flt(awaiting),
		"approved_unpaid_amount": flt(unpaid),
		"currency": currency,
	}


def _unmarked() -> dict:
	"""Days with no attendance row inside the filing window.

	The single most common cause of a wrong payslip, and today invisible until
	payroll — by which point the window to fix it has usually closed. The
	window is the FILING window, so every day counted here is one an Attendance
	Request would still accept.
	"""
	from hrms.api import get_current_employee
	from hrms.utils.filing_window import earliest_filable_date
	from hrms.utils.timezone import employee_now

	employee = get_current_employee()
	if not employee:
		return {"days": 0}

	to_date = employee_now(employee).date()
	from_date = earliest_filable_date(to_date)
	marked = set(
		frappe.get_all(
			"Attendance",
			filters={
				"employee": employee,
				"attendance_date": ("between", [from_date, to_date]),
				"docstatus": ("<", 2),
			},
			pluck="attendance_date",
			ignore_permissions=True,
		)
	)
	# Only days with a PUNCH. A day nobody worked is not an unmarked day — it
	# is a day off, and counting it would put a number on the screen that never
	# goes to zero and that nobody can act on.
	worked = set(
		frappe.get_all(
			"Employee Checkin",
			filters={
				"employee": employee,
				"time": ("between", [f"{from_date} 00:00:00", f"{to_date} 23:59:59"]),
			},
			pluck="shift_actual_start",
			ignore_permissions=True,
		)
	)
	worked_days = {getdate(value) for value in worked if value}
	gaps = sorted(day for day in worked_days if day not in marked)
	logger.info(
		"[requests_summary] unmarked employee=%s window=%s..%s gaps=%d",
		employee,
		from_date,
		to_date,
		len(gaps),
	)
	return {"days": len(gaps), "from_date": str(from_date), "to_date": str(to_date)}


@frappe.whitelist(methods=["GET", "POST"])
def get_requests_summary() -> dict:
	"""Every standing number the Requests screen states, in one call.

	Each section is independent: one failing must not blank the strip, because
	an employee who came to check their leave balance should still get it when
	the overtime lookup is having a bad day. A section that could not be read
	is ABSENT rather than zero — a zero is an answer, and the wrong one.
	"""
	summary = {}
	for key, reader in (
		("leave", _leave),
		("overtime", _overtime),
		("expenses", _expenses),
		("attendance", _unmarked),
	):
		try:
			summary[key] = reader()
		except Exception:
			# Logged loudly with the section named: a strip that silently loses
			# a number looks exactly like a strip reporting zero, and this app
			# has already paid once for a swallow that hid six broken queries.
			logger.exception("[requests_summary] %s failed; omitted", key)

	logger.info("[requests_summary] user=%s sections=%s", frappe.session.user, sorted(summary))
	return summary
