"""Re-stamp a range of punches from the roster as it stands now.

The roster is the source of the shift stamp; the stamp is a cache. Every
Employee Checkin is stamped once, at tap time, from the assignments active at
that moment (the override's `fetch_shift`), and until 21 September 2026 nothing
re-read that cache when the roster changed: a day worker's 24 Aug 02:00 OUT,
filed under a stray 19:30-03:30 night assignment, kept `shift_start = 23 Aug
19:30` for ever — the day was grouped under the wrong shift and Fix Day opened
23 Aug for a 24 Aug row (audit E §5, H3). Only the nightly's 7-day rostered
step repaired it, unguarded, and never past its window.

`restamp` walks the employee's local, unlinked punches of a date range,
oldest first, re-runs the SAME resolution a fresh tap gets on a loaded doc,
and rewrites the stamp hook-free (`frappe.db.set_value`, as the session
re-stamp in the override does). Every shift day a punch left or joined is
then queued for the engine's re-mark. A punch already linked to an Attendance
row whose resolution changed is re-stamped AND released from its row (HR
changed an input, so the output must be recomputed); the queued guarded
rebuild re-pairs it from the right stamps, and the never-worse guard still
protects an automatic lowering. Linked-and-unchanged punches keep their link.

When the roster no longer covers a punch at all, the WHOLE stamp is cleared
(shift, shift_start/end, shift_actual_*, overtime_type None; offshift 1) and
its day is its own clock date: fetch_shift on a loaded doc clears only
`shift`/`offshift`, and a half stamp would keep the old shift day alive.

Oldest first matters: an OUT inherits the stamp of the IN it closes from the
database, so the IN must be written before the OUT is resolved. Two limits
follow: a dry run under-reports an OUT that inherits a re-stamped IN (it
still reads the IN's old stamp), and the read starts at `from_date` 00:00 —
a punch on the day before that now resolves onto `from_date` is outside it.

Entry points: `preview` (whitelisted, HR-only, dry run — how the owner lists
the glitch range before anyone writes) and the Shift Assignment hooks
(hrms/overrides/shift_assignment_hooks.py), which queue the write path.
"""

import logging
from datetime import datetime, time, timedelta

import frappe
from frappe.utils import getdate

from hrms.utils.day_remark import remark_day_after_commit

logger = logging.getLogger(__name__)

HR_ROLES = ("HR User", "HR Manager", "System Manager")
STAMP_FIELDS = (
	"shift",
	"shift_start",
	"shift_end",
	"shift_actual_start",
	"shift_actual_end",
	"overtime_type",
	"offshift",
)
COMPARED_FIELDS = ("shift", "shift_start", "shift_end", "offshift")
# The whole stamp gone, not half of it: a loaded doc's fetch_shift clears only shift/offshift.
CLEARED = {field: None for field in STAMP_FIELDS} | {"offshift": 1}


def restamp(employee, from_date, to_date, *, reason, dry_run=True) -> dict:
	"""Re-resolve the unlinked local punches of `employee` in [from_date, to_date].

	The read runs one day past `to_date`: a night shift's OUT lands after
	midnight. Returns {"planned": [...], "released": [...], "days": [...],
	"applied": bool}; `planned` lists each punch whose stamp differs
	(old -> new), `released` the linked ones among them whose Attendance link
	is cleared, `days` every distinct shift day touched, oldest first.
	"""
	from_date, to_date = getdate(from_date), getdate(to_date)
	rows = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": employee,
			"synced_from_instance": ("is", "not set"),
			"time": (
				"between",
				[
					datetime.combine(from_date, time.min),
					datetime.combine(to_date + timedelta(days=1), time.max),
				],
			),
		},
		fields=["name", "time", "attendance", *COMPARED_FIELDS],
		order_by="time asc",
		limit_page_length=0,
	)
	planned, released, days = [], [], []
	for row in rows:
		old_day = getdate(row.get("shift_start") or row.get("time"))
		doc = frappe.get_doc("Employee Checkin", row["name"])
		old = _stamp(doc)
		# _stamp_shift and _close_open_session both stand down for a linked punch;
		# the resolution must run as if the link were not there.
		doc.attendance = None
		doc.fetch_shift()
		new = _stamp(doc) if doc.shift else dict(CLEARED)
		if _same(old, new):
			continue
		new_day = getdate(new["shift_start"] or doc.time)
		planned.append({"name": row["name"], "time": str(row["time"]), "old": old, "new": new})
		_touch(days, old_day)
		_touch(days, new_day)
		values = dict(new)
		# The write names the link it saw: a punch linked (or re-linked) meanwhile is left alone.
		where = {
			"name": row["name"],
			"synced_from_instance": ("is", "not set"),
			"attendance": row["attendance"] if row.get("attendance") else ("is", "not set"),
		}
		if row.get("attendance"):
			released.append(row["name"])
			values["attendance"] = None
			logger.info("[restamp] %s released from %s: its stamp changed", row["name"], row["attendance"])
		if not dry_run:
			frappe.db.set_value("Employee Checkin", where, values)
	days.sort()
	if not dry_run:
		for day in days:
			remark_day_after_commit(employee, day, reason)
	logger.info(
		"[restamp] %s %s..%s (%s): %d punch(es) re-stamped, %d released from attendance, %d day(s) %s",
		employee,
		from_date,
		to_date,
		reason,
		len(planned),
		len(released),
		len(days),
		"dry run" if dry_run else "queued for re-mark",
	)
	return {
		"planned": planned,
		"released": released,
		"days": [str(day) for day in days],
		"applied": not dry_run,
	}


@frappe.whitelist()
def preview(employee, from_date, to_date) -> dict:
	"""Dry run for the operator: what a roster-driven re-stamp WOULD change.

	There is no apply endpoint on purpose: the write path is the job the
	Shift Assignment hooks queue when HR fixes the roster.
	"""
	frappe.only_for(HR_ROLES)
	_ensure_company_visible(employee)
	return restamp(employee, from_date, to_date, reason=f"preview by {frappe.session.user}", dry_run=True)


def _ensure_company_visible(employee) -> None:
	"""HR role membership and the company fence are two different things in
	this hub (hrms/api/roster.py::_ensure_can_roster is the reference): an HR
	User fenced to company A must not read company B's punches through here."""
	from frappe import _

	from hrms.overrides.company_scope import company_visible

	company = frappe.db.get_value("Employee", employee, "company")
	if company is None:
		frappe.throw(_("Employee {0} does not exist.").format(employee), frappe.DoesNotExistError)
	if not company_visible(company):
		logger.warning("[restamp] %s denied preview of %s (company fence)", frappe.session.user, employee)
		frappe.throw(_("You are not permitted to see this employee's punches."), frappe.PermissionError)


def _stamp(doc) -> dict:
	return {field: getattr(doc, field, None) for field in STAMP_FIELDS}


def _same(old, new) -> bool:
	return all(str(old.get(f) or "") == str(new.get(f) or "") for f in COMPARED_FIELDS)


def _touch(days, day) -> None:
	if day not in days:
		days.append(day)
