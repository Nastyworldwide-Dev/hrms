"""Nightly stale-IN sweeper.

sweep_stale_ins() -- daily 10:00 AM job (registered via hrms/hooks.py
scheduler_events) that tags Employee Checkin IN logs older than
STALE_HOURS hours without a matching OUT as is_abandoned=1, and pings
HR Manager(s) with a count.
"""

from __future__ import annotations

import logging

import frappe
from frappe.utils import add_to_date, get_datetime, now_datetime

from hrms.utils.timezone import employee_now

logger = logging.getLogger(__name__)

STALE_HOURS = 36
# Widest possible gap between the system clock and any attendance timezone
# (UTC-12..UTC+14). The SQL prefilter is loosened by this so no genuinely
# stale row is missed; the exact per-employee cutoff is applied in Python.
MAX_TZ_SPREAD_HOURS = 26
HR_MANAGER_ROLE = "HR Manager"


def sweep_stale_ins() -> int:
	"""Find IN check-ins older than STALE_HOURS with no matching OUT and tag them.

	Skips:
	  - IN rows already tagged is_abandoned=1 (idempotent — re-running won't
	    re-tag the same row)
	  - IN rows that have a later OUT for the same employee
	  - IN rows whose session already has a Remote Checkin Request (i.e.
	    the employee has already submitted a late check-out)

	Notifies every active HR Manager with a single in-app alert per run
	if any rows were tagged.
	"""
	# Prefilter widely on the system clock (oldest first, so real candidates
	# are never crowded out by the wider window), then apply each employee's
	# own cutoff below — stored times are their local wall clock.
	prefilter_cutoff = add_to_date(now_datetime(), hours=-(STALE_HOURS - MAX_TZ_SPREAD_HOURS))
	logger.info("[scheduler] sweep_stale_ins prefilter_cutoff=%s", prefilter_cutoff)

	candidates = frappe.get_all(
		"Employee Checkin",
		filters=[
			["log_type", "=", "IN"],
			["time", "<=", prefilter_cutoff],
			["is_abandoned", "!=", 1],
			# Mirrored punches are owned by their source instance (single-writer,
			# hrms/sync/write_block.py). db.set_value below bypasses doc events,
			# so the exclusion must happen here at the query.
			["synced_from_instance", "is", "not set"],
		],
		fields=["name", "employee", "time"],
		order_by="time asc",
		limit_page_length=500,
	)
	logger.info("[scheduler] sweep_stale_ins candidates=%d", len(candidates))

	tagged = 0
	for row in candidates:
		cutoff = add_to_date(employee_now(row["employee"]), hours=-STALE_HOURS)
		if get_datetime(row["time"]) > cutoff:
			continue
		if _has_matching_close(row):
			continue
		frappe.db.set_value("Employee Checkin", row["name"], "is_abandoned", 1)
		tagged += 1
		logger.warning(
			"[scheduler] Tagged abandoned IN employee=%s checkin=%s time=%s",
			row["employee"],
			row["name"],
			row["time"],
		)

	if tagged > 0:
		_notify_hr(tagged)

	logger.info("[scheduler] sweep_stale_ins -> tagged %d", tagged)
	return tagged


def _has_matching_close(in_row: dict) -> bool:
	"""True if THIS IN's session has a closing OUT or a late-checkout request.

	Session-bounded, matching submit_late_checkout's rule: an OUT (or request)
	only closes this IN when it falls before the employee's NEXT IN. The old
	any-later-OUT check meant a buried forgotten checkout — IN Mon, IN Tue,
	OUT Tue — was never tagged: Tuesday's OUT "closed" Monday's session, so
	HR's abandoned-IN alert stayed silent about the very row the PWA banner
	(get_unresolved_stale_in) was surfacing to the employee. A REJECTED
	late-OUT does not close the session either, mirroring the OT pairing
	engine — the employee must be able to resubmit a corrected time.
	"""
	out_time_filter = [">", in_row["time"]]
	next_in = frappe.db.get_value(
		"Employee Checkin",
		{"employee": in_row["employee"], "log_type": "IN", "time": [">", in_row["time"]]},
		"time",
		order_by="time asc",
	)
	if next_in:
		out_time_filter = ["between", [in_row["time"], next_in]]

	# a bare != would also drop legacy rows with NULL status (SQL three-valued
	# logic), so non-rejected and never-set are probed separately — the same
	# two-probe shape submit_late_checkout uses
	base = {"employee": in_row["employee"], "log_type": "OUT", "time": out_time_filter}
	later_out = frappe.db.exists(
		"Employee Checkin", {**base, "remote_approval_status": ["!=", "Rejected"]}
	) or frappe.db.exists("Employee Checkin", {**base, "remote_approval_status": ["is", "not set"]})
	if later_out:
		logger.info(
			"[scheduler] skip %s — session-closing OUT exists for employee=%s",
			in_row["name"],
			in_row["employee"],
		)
		return True

	request_filters = {
		"employee": in_row["employee"],
		"log_type": "OUT",
		"checkin_time": out_time_filter if not next_in else ["between", [in_row["time"], next_in]],
		"status": ["!=", "Rejected"],
	}
	pending_request = frappe.db.exists("Remote Checkin Request", request_filters)
	if pending_request:
		logger.info(
			"[scheduler] skip %s — late-checkout request exists for employee=%s",
			in_row["name"],
			in_row["employee"],
		)
		return True

	return False


def _notify_hr(count: int) -> None:
	"""One in-app alert per HR Manager per sweep run when abandoned INs exist."""
	hr_users = frappe.get_all(
		"Has Role",
		filters={"role": HR_MANAGER_ROLE, "parenttype": "User"},
		pluck="parent",
	)
	if not hr_users:
		logger.warning("[scheduler] No HR Manager users to notify about %d abandoned INs", count)
		return

	subject = f"{count} abandoned check-in(s) detected"
	body = (
		f"{count} employee check-in(s) older than {STALE_HOURS} hours have no "
		f"matching check-out and were not closed via the late-checkout flow. "
		f"Filter the Employee Checkin list by 'Is Abandoned = Yes' to review."
	)
	for user in set(hr_users):
		try:
			frappe.get_doc(
				{
					"doctype": "Notification Log",
					"for_user": user,
					"type": "Alert",
					"document_type": "Employee Checkin",
					"subject": subject,
					"email_content": body,
				}
			).insert(ignore_permissions=True)
			logger.info("[scheduler] notified HR user=%s count=%d", user, count)
		except Exception as exc:
			logger.warning("[scheduler] HR notify failed user=%s: %s", user, exc)
