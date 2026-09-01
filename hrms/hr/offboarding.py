"""Employee offboarding automation.

Two promises, both driven by the authoritative Employee fields
(resignation_letter_date, notice_number_of_days, relieving_date) —
no parallel offboarding record:

* When the relieving date changes, every submitted, unexpired Leave
  Allocation of the employee is prorated to the relieving date via the
  allocation's own post-submit update path (``on_update_after_submit``
  revalidates and writes the delta to the Leave Ledger). The full-period
  entitlement is parked in ``pre_offboarding_leaves`` so a moved or
  cancelled relieving date restores it exactly. Deterministic and
  idempotent: the target is recomputed from the baseline every time, so
  re-saving the Employee never compounds a reduction.

* A daily scheduler flips Active -> Left once the configured number of
  WORKING days (HR Settings, default 3) has passed after the relieving
  date, counted against the employee's own Holiday List.
"""

import datetime
import logging

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# pure policy functions (bench-free testable — no frappe at call time)
# ---------------------------------------------------------------------------


def prorate_to_relieving(full_leaves: float, from_date, to_date, relieving_date) -> float:
	"""Entitlement earned from from_date up to the relieving date, inclusive.

	Mirrors the rounding convention of Leave Policy Assignment's
	``calculate_pro_rated_leaves`` (whole days, banker's rounding).
	"""
	if relieving_date >= to_date:
		return full_leaves
	if relieving_date < from_date:
		return 0.0
	eligible_days = (relieving_date - from_date).days + 1
	period_days = (to_date - from_date).days + 1
	return float(round(full_leaves * eligible_days / period_days))


def working_day_offset(start_date, working_days: int, holiday_dates: set) -> datetime.date:
	"""Date of the Nth working day strictly after start_date.

	A day is a working day when it is not in ``holiday_dates`` (the
	employee's Holiday List rows — weekly offs included).
	"""
	day, remaining = start_date, working_days
	while remaining > 0:
		day = day + datetime.timedelta(days=1)
		if day not in holiday_dates:
			remaining -= 1
	return day


def plan_allocation_targets(allocations, relieving_date) -> list[dict]:
	"""Decide the target new_leaves_allocated for each allocation.

	``allocations``: dicts with name, from_date, to_date (dates),
	new_leaves_allocated, unused_leaves, pre_offboarding_leaves,
	leaves_taken, is_scheduler_managed. ``relieving_date``: date or None
	(None = offboarding cancelled -> restore baselines).

	Returns only the rows that need a change. Never plans below the
	leaves already taken (the allocation's own validation would refuse),
	and never touches scheduler-managed (earned leave) allocations.
	"""
	plans = []
	for allocation in allocations:
		if allocation.get("is_scheduler_managed"):
			continue
		baseline = flt(allocation.get("pre_offboarding_leaves")) or flt(allocation["new_leaves_allocated"])
		if relieving_date is None or relieving_date >= allocation["to_date"]:
			target, marker = baseline, 0.0
		else:
			target = prorate_to_relieving(
				baseline, allocation["from_date"], allocation["to_date"], relieving_date
			)
			taken_floor = flt(allocation.get("leaves_taken")) - flt(allocation.get("unused_leaves"))
			target = max(target, taken_floor, 0.0)
			marker = baseline
		if flt(target) != flt(allocation["new_leaves_allocated"]) or flt(marker) != flt(
			allocation.get("pre_offboarding_leaves")
		):
			plans.append(
				{
					"name": allocation["name"],
					"new_leaves_allocated": flt(target),
					"pre_offboarding_leaves": flt(marker),
				}
			)
	return plans


# ---------------------------------------------------------------------------
# Employee hooks
# ---------------------------------------------------------------------------


def validate_offboarding_dates(doc, method=None):
	"""Employee.validate — contradictory offboarding dates never save."""
	if not doc.relieving_date:
		return
	relieving_date = getdate(doc.relieving_date)
	if doc.resignation_letter_date and relieving_date < getdate(doc.resignation_letter_date):
		frappe.throw(
			_("Relieving Date cannot be before the Resignation Letter Date"),
			title=_("Invalid Offboarding Dates"),
		)
	if doc.date_of_joining and relieving_date < getdate(doc.date_of_joining):
		frappe.throw(
			_("Relieving Date cannot be before the Date of Joining"),
			title=_("Invalid Offboarding Dates"),
		)


def prorate_leave_allocations(doc, method=None):
	"""Employee.on_update — prorate leave to the relieving date.

	Runs only when relieving_date actually changed. Mirrored employees are
	owned by their source instance (single-writer, hrms/sync/write_block.py)
	and are never touched.
	"""
	if doc.get("synced_from_instance"):
		return
	if not doc.has_value_changed("relieving_date"):
		return

	from hrms.hr.doctype.leave_application.leave_application import get_approved_leaves_for_period

	relieving_date = getdate(doc.relieving_date) if doc.relieving_date else None
	allocations = frappe.get_all(
		"Leave Allocation",
		filters={"employee": doc.name, "docstatus": 1, "expired": 0},
		fields=[
			"name",
			"leave_type",
			"from_date",
			"to_date",
			"new_leaves_allocated",
			"unused_leaves",
			"pre_offboarding_leaves",
			"leave_policy_assignment",
		],
	)
	if not allocations:
		return

	earned_leave_types = {
		row.name
		for row in frappe.get_all(
			"Leave Type",
			filters={"name": ["in", list({a.leave_type for a in allocations})], "is_earned_leave": 1},
		)
	}
	for allocation in allocations:
		# Earned-leave allocations under a policy are scheduler-managed;
		# their own on_update_after_submit refuses manual edits.
		allocation["is_scheduler_managed"] = bool(
			allocation.leave_policy_assignment and allocation.leave_type in earned_leave_types
		)
		allocation["from_date"] = getdate(allocation.from_date)
		allocation["to_date"] = getdate(allocation.to_date)
		allocation["leaves_taken"] = get_approved_leaves_for_period(
			doc.name, allocation.leave_type, allocation.from_date, allocation.to_date
		)

	plans = plan_allocation_targets(allocations, relieving_date)
	logger.info(
		"[offboarding] relieving_date=%s for %s: %d allocation(s), %d to adjust",
		relieving_date,
		doc.name,
		len(allocations),
		len(plans),
	)

	for plan in plans:
		frappe.db.savepoint("offboarding_proration")
		try:
			allocation_doc = frappe.get_doc("Leave Allocation", plan["name"])
			allocation_doc.pre_offboarding_leaves = plan["pre_offboarding_leaves"]
			allocation_doc.new_leaves_allocated = plan["new_leaves_allocated"]
			allocation_doc.flags.ignore_permissions = True
			allocation_doc.save()
			allocation_doc.add_comment(
				"Comment",
				_("Leave allocation set to {0} for offboarding (relieving date: {1})").format(
					plan["new_leaves_allocated"], relieving_date or _("cancelled")
				),
			)
			logger.info(
				"[offboarding] %s new_leaves_allocated -> %s",
				plan["name"],
				plan["new_leaves_allocated"],
			)
		except Exception:
			frappe.db.rollback(save_point="offboarding_proration")
			logger.exception("[offboarding] proration failed for %s", plan["name"])
			frappe.log_error(
				title=f"Offboarding leave proration failed for {doc.name} ({plan['name']})",
				message=frappe.get_traceback(),
			)


# ---------------------------------------------------------------------------
# daily scheduler
# ---------------------------------------------------------------------------


def get_holidays_after(employee: str, relieving_date, working_days: int) -> set:
	"""Holiday dates (weekly offs included) just after the relieving date,
	from the employee's own Holiday List (company fallback built in)."""
	from hrms.utils.holiday_list import get_holiday_dates_between, get_holiday_list_for_employee

	holiday_list = get_holiday_list_for_employee(employee, raise_exception=False, as_on=relieving_date)
	if not holiday_list:
		# No holiday list anywhere -> every day counts as a working day.
		return set()
	# ponytail: fixed lookahead window; a holiday list ending inside it makes
	# later days count as working. Widen the window if that ever matters.
	window_end = add_days(relieving_date, working_days * 7 + 31)
	return {
		getdate(day)
		for day in get_holiday_dates_between(holiday_list, add_days(relieving_date, 1), window_end)
	}


def update_relieved_employee_status() -> dict:
	"""Daily scheduler — Active -> Left after the configured working days.

	The threshold (HR Settings, default 3) is counted in WORKING days after
	the relieving date against the employee's Holiday List. Safe to rerun:
	the query only sees Active employees, and each candidate is re-checked
	on its live document before the flip, so an employee whose status or
	relieving date changed since the query is never forced.
	"""
	working_days = (
		cint(frappe.db.get_single_value("HR Settings", "exit_status_change_after_working_days")) or 3
	)
	today = getdate()
	candidates = frappe.get_all(
		"Employee",
		filters=[
			["status", "=", "Active"],
			["relieving_date", "is", "set"],
			["relieving_date", "<=", today],
			# Mirrored employees are owned by their source instance
			# (single-writer, hrms/sync/write_block.py).
			["synced_from_instance", "is", "not set"],
		],
		fields=["name", "relieving_date"],
	)
	logger.info(
		"[offboarding] status sweep: %d candidate(s), threshold %d working day(s)",
		len(candidates),
		working_days,
	)

	counters = {"marked_left": 0, "waiting": 0, "error": 0}
	for row in candidates:
		# savepoint per employee: one bad record must not poison the rest
		frappe.db.savepoint("offboarding_status")
		try:
			relieving_date = getdate(row["relieving_date"])
			threshold = working_day_offset(
				relieving_date, working_days, get_holidays_after(row["name"], relieving_date, working_days)
			)
			if today < threshold:
				counters["waiting"] += 1
				continue
			employee = frappe.get_doc("Employee", row["name"])
			if (
				employee.status != "Active"
				or not employee.relieving_date
				or getdate(employee.relieving_date) != relieving_date
			):
				# criteria changed between the query and now — never force
				counters["waiting"] += 1
				continue
			employee.status = "Left"
			employee.flags.ignore_permissions = True
			employee.save()
			employee.add_comment(
				"Comment",
				_("Status set to Left automatically: {0} working day(s) after relieving date {1}").format(
					working_days, relieving_date
				),
			)
			counters["marked_left"] += 1
			logger.info("[offboarding] %s marked Left (relieved %s)", row["name"], relieving_date)
		except Exception:
			frappe.db.rollback(save_point="offboarding_status")
			counters["error"] += 1
			logger.exception("[offboarding] status transition failed for %s", row["name"])
			frappe.log_error(
				title=f"Offboarding status transition failed for {row['name']}",
				message=frappe.get_traceback(),
			)

	logger.info("[offboarding] status sweep done: %s", counters)
	return counters
