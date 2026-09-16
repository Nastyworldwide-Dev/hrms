"""Who owns an Attendance row — read from evidence, never from a blank tick.

`auto_attendance` was added on 1 September 2026 (aaa56fe04) with default 0 and
no backfill, and ERP-mirrored rows never carry it. Everything that asks "did HR
write this?" by reading that one field therefore answers YES for almost every
row older than that date and for every mirrored row:
`attendance_recovery.protected_reason` returns "was marked by HR by hand", the
automatic fixes skip the day, and the live run reported "fixed 8, 73 need HR"
while HR-EMP-00313 read Present (HR) / Half Day (HR) / Absent (HR) across a
month nobody had touched.

This module answers the question from what actually happened to the row:

* `classify_row` — PURE. The row's fields, its Version history and (for a
  mirrored row) the ERP side, in one truth table.
* `classify_day` / `classify_window` — the DB-reading wrappers. Every read is
  batched: one Attendance query, one Version query, one Employee Checkin query,
  one Comment query for the whole window, whatever its size.
* `is_system_owned` — what other modules call instead of reading
  `auto_attendance` directly.
* `relabel_system_rows` — writes `auto_attendance = 1` back onto rows this
  module proves are system-made, and onto nothing else. Behind an HR Settings
  switch that is off until HR turns it on, and a pilot list that fences a run
  to named employees.

Four owners, and UNSURE is treated as HR's by every caller. Fail safe: a row we
cannot prove the machine made is a row the machine does not touch.

	PYTHONPATH=. python3 hrms/tests/test_attendance_ownership.py
"""

from __future__ import annotations

import json
import logging

import frappe
from frappe import _
from frappe.utils import cint, getdate

from hrms.utils import hr_removed_day
from hrms.utils.dry_run import wants_dry_run

logger = logging.getLogger(__name__)

#: A person in the Desk wrote this row: automation leaves it alone.
OWNER_HR = "hr"
#: A leave, a half-day leave or an Attendance Request speaks for the day.
OWNER_REQUEST = "request"
#: The hourly job, the recovery, the ERP import or the old system's own job made it.
OWNER_SYSTEM = "system"
#: The evidence does not settle it. Treated as HR's everywhere.
OWNER_UNSURE = "unsure"

OWNERS = (OWNER_HR, OWNER_REQUEST, OWNER_SYSTEM, OWNER_UNSURE)

#: Sessions that are never a person acting in the Desk. The scheduler and every
#: background job run as Administrator (attendance_auto_recovery sets it).
SYSTEM_USERS = frozenset({"Administrator", "Guest", "", None})

#: Changing one of these is changing what the day SAYS; anything else (a shift
#: stamp, a link, a comment) is bookkeeping and does not hand the row over.
DECIDING_FIELDS = ("status", "in_time", "out_time", "working_hours")

#: The HR master edit's own comment (attendance_master_edit._save).
MASTER_EDIT_MARKER = "via Shift Attendance"

#: HR Settings write switch (Custom Field, patches/v16_0/attendance_recovery_switches.py).
#: An absent field reads as OFF: a deploy lands with nothing relabelled.
RELABEL_SWITCH = "attendance_ownership_relabel"
#: HR Settings pilot list (Custom Field, comma-separated employee ids). Empty = everyone.
PILOT_FIELD = "attendance_rebuild_pilot_employees"

#: Fields `classify_row` reads. Kept as one list so the wrappers cannot drift.
OWNERSHIP_FIELDS = (
	"name",
	"employee",
	"employee_name",
	"attendance_date",
	"status",
	"docstatus",
	"auto_attendance",
	"leave_type",
	"leave_application",
	"attendance_request",
	"modify_half_day_status",
	"working_hours",
	"in_time",
	"out_time",
	"shift",
	"owner",
	"amended_from",
)


# --- pure ---------------------------------------------------------------------------


def is_real_user(user, system_users=()) -> bool:
	"""Is this a person, rather than the framework or a sync account? Pure."""
	if user in SYSTEM_USERS:
		return False
	return user not in set(system_users or ())


def changed_fields(entry) -> set:
	"""The fieldnames one `tabVersion` row records as changed. Pure.

	Frappe stores `{"changed": [[fieldname, old, new], …]}`; a row written by an
	older version, or by a patch, can carry anything — an unreadable entry
	proves nothing and contributes nothing.
	"""
	data = entry.get("data") if hasattr(entry, "get") else None
	if isinstance(data, str):
		try:
			data = json.loads(data or "{}")
		except (ValueError, TypeError):
			logger.warning("[attendance_ownership] unreadable version data on %s", entry.get("docname"))
			return set()
	if not isinstance(data, dict):
		return set()
	return {change[0] for change in data.get("changed") or [] if change}


def _punch_count(row) -> int:
	punches = row.get("punches")
	if punches is None:
		return 0
	if isinstance(punches, int):
		return punches
	return len(punches)


def classify_row(row, versions=None, source=None) -> tuple[str, str]:
	"""(owner, reason) for ONE Attendance row. PURE — no database.

	`row`: the fields in OWNERSHIP_FIELDS plus `punches` (how many Employee
	Checkins are linked to it) and `synced_from_instance`.
	`versions`: that row's `tabVersion` entries ({owner, data}).
	`source`: what only the wrappers can know — `hr_master_edit` / `hr_removed`
	(the two HR markers), `erp_owner` (the owner of the mirrored row on the old
	instance) and `system_users` (extra accounts that are not people, e.g. the
	sync user).

	The order is the order of certainty: a request owns its own day; an HR
	marker is a person saying so; a Version entry is a person doing so; then
	creation, then the machine's own signature. Anything left is UNSURE.
	"""
	source = source or {}
	versions = versions or []
	extra_system = set(source.get("system_users") or ())
	name = row.get("name")

	if row.get("leave_type") or row.get("leave_application") or row.get("status") == "On Leave":
		return OWNER_REQUEST, f"{name} is a leave record"
	if cint(row.get("modify_half_day_status")):
		return OWNER_REQUEST, f"{name} is a half-day leave"
	if row.get("attendance_request"):
		return OWNER_REQUEST, f"{name} comes from an Attendance Request"

	if source.get("hr_removed"):
		return OWNER_HR, "HR removed this day in Shift Attendance"
	if source.get("hr_master_edit"):
		return OWNER_HR, "HR wrote this row in the Shift Attendance master edit"

	for entry in versions:
		if not entry:
			continue
		editor = entry.get("owner")
		if not is_real_user(editor, extra_system):
			continue
		touched = sorted(changed_fields(entry) & set(DECIDING_FIELDS))
		if touched:
			return OWNER_HR, f"{editor} changed {', '.join(touched)}"

	creator = row.get("owner")
	person_made_it = is_real_user(creator, extra_system)
	if row.get("amended_from") and person_made_it:
		return OWNER_HR, f"{creator} amended {row.get('amended_from')}"
	if person_made_it and not _punch_count(row):
		return OWNER_HR, f"{creator} created it with no punch behind it"

	mirrored = row.get("synced_from_instance")
	if mirrored:
		erp_owner = source.get("erp_owner")
		if erp_owner is not None:
			if is_real_user(erp_owner, extra_system):
				return OWNER_HR, f"{erp_owner} wrote it on {mirrored}"
			return OWNER_SYSTEM, f"copied from {mirrored}, where {erp_owner} made it"
		if not person_made_it:
			return OWNER_SYSTEM, f"copied from {mirrored} by {creator}"
		return OWNER_UNSURE, f"copied from {mirrored}; who made it there is not recorded here"

	if not person_made_it:
		punches = _punch_count(row)
		if punches:
			return OWNER_SYSTEM, f"{creator} marked it from {punches} linked punch(es)"
		if row.get("amended_from"):
			return OWNER_SYSTEM, f"{creator} amended {row.get('amended_from')}"
		# Punchless and machine-created: the hourly Absent sweep's own shape. It
		# marks a day Absent precisely because no punch arrived, so "no punches"
		# is the evidence, not the absence of it. Nothing on this hub creates
		# Attendance from a console — every fix ships as a patch or a hook — so
		# an Administrator-owned punchless row is the sweep's, not a person's.
		return OWNER_SYSTEM, f"{creator} created it and no person has touched it"

	return OWNER_UNSURE, f"{creator} created it with punches linked and no version entry settles it"


def is_system_owned(row, versions=None, source=None) -> bool:
	"""Did the machine make this row? Call this instead of reading `auto_attendance`."""
	return classify_row(row, versions=versions, source=source)[0] == OWNER_SYSTEM


# --- database wrappers ----------------------------------------------------------------


def _versions_by_row(names) -> dict:
	"""Every `tabVersion` entry for these rows, in ONE query. {docname: [entry]}."""
	out: dict[str, list] = {}
	if not names:
		return out
	for entry in frappe.get_all(
		"Version",
		filters={"ref_doctype": "Attendance", "docname": ["in", sorted(names)]},
		fields=["docname", "owner", "data"],
		limit_page_length=0,
	):
		out.setdefault(entry.get("docname"), []).append(entry)
	logger.debug("[attendance_ownership] %d row(s) carry version history", len(out))
	return out


def _punches_by_row(names) -> dict:
	"""How many Employee Checkins are linked to each row, in ONE query."""
	out: dict[str, int] = {}
	if not names:
		return out
	for punch in frappe.get_all(
		"Employee Checkin",
		filters={"attendance": ["in", sorted(names)]},
		fields=["attendance"],
		limit_page_length=0,
	):
		key = punch.get("attendance")
		out[key] = out.get(key, 0) + 1
	return out


def _master_edited(names) -> set:
	"""Rows carrying the HR master edit's comment, in ONE query."""
	if not names:
		return set()
	return {
		comment.get("reference_name")
		for comment in frappe.get_all(
			"Comment",
			filters={"reference_doctype": "Attendance", "reference_name": ["in", sorted(names)]},
			fields=["reference_name", "content"],
			limit_page_length=0,
		)
		if MASTER_EDIT_MARKER in (comment.get("content") or "")
	}


def _removed_days(employees, start, end) -> dict:
	"""{employee: {day}} HR removed in the editor — one query per employee, not per row."""
	return {employee: hr_removed_day.removed_days(employee, start, end) for employee in sorted(employees)}


def classify_window(from_date, to_date, employees=None, system_users=None, erp_owners=None) -> list[dict]:
	"""One verdict per live Attendance row in [from_date, to_date].

	Rows are read once, and so is every piece of evidence: the Version history,
	the linked punches and the master-edit comments come back in one query each
	however many rows the window holds.

	Two things this hub cannot see for itself, so a caller that knows them says
	so: `system_users`, the accounts that are not people (a dedicated sync or
	API account beside Administrator), and `erp_owners`, {attendance name: who
	owns the row on the old instance}. Without them a mirrored row falls back to
	who copied it here, which is the safe direction — a mirrored row a person
	may have written reads HR, never system.
	"""
	start, end = getdate(from_date), getdate(to_date)
	filters = {"attendance_date": ["between", [str(start), str(end)]], "docstatus": ["<", 2]}
	if employees:
		filters["employee"] = ["in", sorted(employees)]
	rows = frappe.get_all(
		"Attendance",
		filters=filters,
		fields=[*OWNERSHIP_FIELDS, "synced_from_instance"],
		order_by="employee asc, attendance_date asc",
		limit_page_length=0,
	)
	names = {row.get("name") for row in rows if row.get("name")}
	versions = _versions_by_row(names)
	punches = _punches_by_row(names)
	edited = _master_edited(names)
	removed = _removed_days({row.get("employee") for row in rows if row.get("employee")}, start, end)

	out = []
	for row in rows:
		day = getdate(row.get("attendance_date"))
		payload = dict(row)
		payload["punches"] = punches.get(row.get("name"), 0)
		source = {
			"hr_master_edit": row.get("name") in edited,
			"hr_removed": day in removed.get(row.get("employee"), set()),
			"system_users": system_users or (),
			"erp_owner": (erp_owners or {}).get(row.get("name")),
		}
		owner, reason = classify_row(payload, versions.get(row.get("name")), source)
		out.append(
			{
				"employee": row.get("employee"),
				"employee_name": row.get("employee_name"),
				"date": str(day),
				"attendance": row.get("name"),
				"status": row.get("status"),
				"working_hours": row.get("working_hours"),
				"shift": row.get("shift"),
				"docstatus": cint(row.get("docstatus")),
				"auto_attendance": cint(row.get("auto_attendance")),
				"owner": owner,
				"reason": reason,
				"would_relabel": owner == OWNER_SYSTEM and not cint(row.get("auto_attendance")),
				"punches": payload["punches"],
			}
		)
	logger.info(
		"[attendance_ownership] %s..%s: %d row(s), %d system-made with the tick off",
		start,
		end,
		len(out),
		sum(1 for r in out if r["would_relabel"]),
	)
	return out


def classify_day(employee: str, day, system_users=None, erp_owners=None) -> list[dict]:
	"""Every live Attendance row of one employee-day, classified."""
	return classify_window(day, day, employees=[employee], system_users=system_users, erp_owners=erp_owners)


def owner_counts(rows) -> dict:
	"""How many rows per label. Pure."""
	return {owner: sum(1 for row in rows if row.get("owner") == owner) for owner in OWNERS}


# --- relabel -------------------------------------------------------------------------


def relabel_enabled() -> bool:
	"""The HR Settings write switch. An absent Custom Field reads as OFF."""
	return bool(cint(frappe.get_single("HR Settings").get(RELABEL_SWITCH)))


def pilot_employees() -> list[str]:
	"""The pilot list from HR Settings. Empty (or absent) means everyone."""
	raw = frappe.get_single("HR Settings").get(PILOT_FIELD) or ""
	return [part.strip() for part in str(raw).split(",") if part.strip()]


def _lock(employee: str) -> None:
	"""The per-employee lock HR's master edit and the hourly job take."""
	from hrms.hr.doctype.shift_type.shift_type import lock_employee_row

	lock_employee_row(employee)


def _comment(name: str, text: str) -> None:
	frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Comment",
			"reference_doctype": "Attendance",
			"reference_name": name,
			"content": text,
		}
	).insert(ignore_permissions=True)


def relabel_system_rows(from_date, to_date, employees=None, dry_run=1) -> dict:
	"""Give system-made rows their `auto_attendance` tick back. Dry run by default.

	Only rows `classify_row` proves the machine made are touched: an HR row, a
	leave or request row and an UNSURE row are counted and left exactly as they
	are. Idempotent — a row that already carries the tick is not written again —
	and refused outright while the HR Settings switch is off, so a deploy lands
	with nothing changed. When the pilot list is set, only those employees are
	read at all.
	"""
	dry = wants_dry_run(dry_run)
	if not relabel_enabled():
		logger.info("[attendance_ownership] relabel refused: %s is off", RELABEL_SWITCH)
		return {
			"ok": False,
			"dry_run": dry,
			"refused": _("HR Settings switch {0} is off").format(RELABEL_SWITCH),
			"changed": [],
			"counts": {},
			"pilot": [],
		}

	pilot = pilot_employees()
	wanted = sorted(set(employees) & set(pilot)) if (employees and pilot) else (employees or pilot or None)
	if wanted == []:
		# Asked for employees, none of them on the pilot list. An empty list is
		# falsy further down, which would read as "no filter" and scan the whole
		# window to throw all of it away.
		logger.info("[attendance_ownership] relabel: nothing asked for is on the pilot list")
		return {"ok": True, "dry_run": dry, "pilot": pilot, "counts": {}, "changed": [], "scanned": 0}
	rows = classify_window(from_date, to_date, employees=wanted)
	if pilot:
		# The list is the fence, not a hint: a row outside it is never written,
		# whatever the caller asked for or the window returned.
		rows = [row for row in rows if row.get("employee") in set(pilot)]
	targets = [row for row in rows if row.get("would_relabel")]

	changed = []
	for row in targets:
		if dry:
			changed.append(row)
			continue
		_lock(row["employee"])
		frappe.db.set_value("Attendance", row["attendance"], "auto_attendance", 1, update_modified=False)
		_comment(
			row["attendance"],
			_("Ownership check: system-made — {0}. auto_attendance set back to 1.").format(row["reason"]),
		)
		changed.append(row)

	result = {
		"ok": True,
		"dry_run": dry,
		"pilot": pilot,
		"counts": owner_counts(rows),
		"changed": changed,
		"scanned": len(rows),
	}
	logger.info(
		"[attendance_ownership] relabel %s..%s: %d of %d row(s) %s",
		getdate(from_date),
		getdate(to_date),
		len(changed),
		len(rows),
		"would be relabelled" if dry else "relabelled",
	)
	return result


def relabel_preview(from_date, to_date, employees=None) -> dict:
	"""What a relabel would do, without the switch mattering. Read-only."""
	rows = classify_window(from_date, to_date, employees=employees)
	return {"counts": owner_counts(rows), "would_relabel": [r for r in rows if r["would_relabel"]]}
