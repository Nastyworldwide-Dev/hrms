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

import logging

import frappe
from frappe import _
from frappe.utils import flt, getdate

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
