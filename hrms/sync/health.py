"""A sync that stops running says so.

`run_sync` is `@frappe.whitelist(methods=["POST"])` and appears in **no**
`scheduler_events` entry: a human presses it or the mirror does not move.
`runner._notify_run_finished` already reports the outcome of a run, but it
addresses `frappe.session.user` — whoever pressed the button. So a run that
FAILS is audible to one person, and a run that never happens is audible to
nobody.

That gap has the exact shape of the symptom it was written for: employee and
check-in rows that simply stop, with no error anywhere, because the last person
to press the button stopped pressing it. The mirror does not decay loudly. It
holds the last good data and looks fine.

Three things are deliberately NOT counted as a heartbeat:

  Failed    rows were not written; nothing moved
  Partial   rows were left unwritten and the watermark was HELD, so the next
            run re-reads the same window — a Partial that repeats is a mirror
            standing still while reporting activity
  Running   an unfinished run is not evidence of a finished one

This is DETECTIVE ONLY. It never starts a sync. Whether the pull should run
unattended is a product decision about writing to a mirror with no human
present — `hrms/sync/write_block.py` exists because that question is taken
seriously here — and it is not one this module makes.

It reports the way `company_fence.report_unfenced_hr_users` reports its own
holes: one Error Log entry, Desk-visible, naming every instance at once rather
than one entry each.
"""

from __future__ import annotations

import logging

import frappe
from frappe.utils import get_datetime, now_datetime

logger = logging.getLogger(__name__)

#: How long an enabled instance may go without a clean run before it is named.
#:
#: 36 hours, not 24: a daily operator cadence plus a missed morning is normal
#: and should not cry wolf, while two missed days is not.
#:
#: ponytail: one constant for every instance. Make it a field on HRMS ERP
#: Instance if one source genuinely syncs on a different cadence.
STALE_AFTER_HOURS = 36

#: The only status that proves the mirror moved. See the module docstring for
#: why Partial is not on this list.
HEARTBEAT_STATUS = "Completed"


def _last_clean_run(instance_name: str):
	rows = frappe.get_all(
		"HRMS Sync Run",
		filters={"source_instance": instance_name, "status": HEARTBEAT_STATUS},
		fields=["name", "finished_at"],
		order_by="finished_at desc",
		limit=1,
	)
	return rows[0] if rows else None


def stale_instances() -> list[dict]:
	"""Enabled instances with no clean run inside the window. Pure query, no writes."""
	now = now_datetime()
	stale = []
	for instance in frappe.get_all("HRMS ERP Instance", filters={"enabled": 1}, pluck="name"):
		last = _last_clean_run(instance)
		if not last or not last.get("finished_at"):
			stale.append({"instance": instance, "reason": "never", "hours": None, "run": None})
			continue
		hours = (now - get_datetime(last["finished_at"])).total_seconds() / 3600
		if hours > STALE_AFTER_HOURS:
			stale.append(
				{"instance": instance, "reason": "stale", "hours": round(hours, 1), "run": last["name"]}
			)
	return stale


def report_stale_instances() -> list[dict]:
	"""Name every instance whose mirror has stopped moving. Daily scheduler entry."""
	stale = stale_instances()
	if not stale:
		logger.info("[sync.health] every enabled instance has a clean run inside %sh", STALE_AFTER_HOURS)
		return []

	lines = []
	for row in stale:
		if row["reason"] == "never":
			lines.append(f"{row['instance']}: no completed run has ever been recorded")
		else:
			lines.append(f"{row['instance']}: last completed run was {row['hours']}h ago ({row['run']})")

	logger.warning("[sync.health] %d instance(s) not syncing: %s", len(stale), lines)
	frappe.log_error(
		title=f"{len(stale)} ERP instance(s) have stopped syncing",
		message=(
			"These instances are enabled but have no Completed sync run in the last "
			f"{STALE_AFTER_HOURS} hours, so their mirrored Employee, Attendance, "
			"Employee Checkin and Leave rows are as old as the date shown.\n\n"
			+ "\n".join(lines)
			+ "\n\nThe pull is operator-initiated: HR Setup -> Data Migration -> ERP "
			"Instance -> Sync Now. A Partial or Failed run does not count here, "
			"because a held watermark means the mirror did not move."
		),
	)
	return stale
