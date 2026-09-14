"""Which source-ERP punches in a window never reached this hub. Read-only.

After cutover (`unlock_mirrored_writes` on the HRMS ERP Instance) the pull no
longer carries Employee Checkin (`hrms.sync.cutover`), and parity stops grading
it. Staff who still punch on the source ERP therefore leave rows there that this
hub never sees — an IN on 3 September with its OUT at 01:04 the next morning,
absent here — and nothing reports the gap.

This report names it. It never writes, on either side:

* the remote is read through `RemoteInstanceClient`, which can only issue GET;
* the local side is one bounded `frappe.get_all`;
* nothing is inserted, stamped, logged to a doctype or committed.

A punch is identified by its natural key, (employee, time to the second,
log_type), never by name: both sites number `EMP-CKIN-.MM.-.YYYY.-.######` from
independent counters, so the same name is routinely two different punches.
Employees map by name, exactly as the mirror writes them (`runner._write_row`
upserts on the source's document name), so a source employee with no local
Employee of that name is listed as unmapped rather than dropped.

    bench --site <site> execute hrms.sync.missing_checkins.report \
        --kwargs '{"from_date": "2026-09-01", "to_date": "2026-09-14"}'
"""

import logging
from collections import Counter
from datetime import date, datetime, timedelta

import frappe
from frappe import _

logger = logging.getLogger(__name__)

DOCTYPE = "Employee Checkin"
DEFAULT_WINDOW_DAYS = 14
#: Each report pages every punch in the window off live production. Refused, not clipped.
MAX_WINDOW_DAYS = 62
#: Local rows are read this far past each edge, so a boundary punch is not missed.
LOCAL_SLACK = timedelta(days=1)
#: An OUT before this hour belongs to the previous day's shift.
PAST_MIDNIGHT_HOUR = 6
MAX_SAMPLE = 500
REMOTE_FIELDS = ["name", "employee", "time", "log_type", "device_id"]
LOCAL_FIELDS = ["name", "employee", "time", "log_type"]


# --- pure ---------------------------------------------------------------------


def _to_second(value) -> datetime:
	"""Naive wall-clock datetime truncated to the second.

	Both sites store punch times as naive wall clock, and the source's JSON sends
	them as strings, sometimes with microseconds. An offset, if one ever appears,
	is dropped rather than converted: converting would move a wall-clock time.
	"""
	moment = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).strip())
	return moment.replace(microsecond=0, tzinfo=None)


def _to_date(value) -> date:
	if isinstance(value, datetime):
		return value.date()
	if isinstance(value, date):
		return value
	return date.fromisoformat(str(value).strip()[:10])


def is_past_midnight(log_type, moment: datetime) -> bool:
	return log_type == "OUT" and moment.hour < PAST_MIDNIGHT_HOUR


def diff_punches(remote_rows, local_rows) -> dict:
	"""Source punches with no matching hub punch. Pure.

	An exact natural-key match is consumed first; only then is a leftover source
	punch checked for a hub punch at the same employee and second under another
	log type (`type_mismatch` — the hub may hold an IN where the source says
	OUT). Matching is one-to-one, so two identical source punches need two here.
	"""
	# Unconsumed hub punch names per natural key.
	local_names: dict[tuple, list] = {}
	for row in local_rows:
		key = (row.get("employee"), _to_second(row.get("time")), row.get("log_type") or "")
		local_names.setdefault(key, []).append(row.get("name"))

	normalised = sorted(
		(
			{**row, "time": _to_second(row.get("time")), "log_type": row.get("log_type") or ""}
			for row in remote_rows
		),
		key=lambda row: (row.get("employee") or "", row["time"], row.get("name") or ""),
	)

	matched = 0
	unmatched = []
	for row in normalised:
		names = local_names.get((row.get("employee"), row["time"], row["log_type"]))
		if names:
			names.pop(0)
			matched += 1
		else:
			unmatched.append(row)

	# What the exact pass left over, by (employee, second), for the type check.
	local_at_moment: dict[tuple, list] = {}
	for (employee, moment, log_type), names in local_names.items():
		for name in names:
			local_at_moment.setdefault((employee, moment), []).append({"log_type": log_type, "name": name})

	missing, type_mismatch = [], []
	for row in unmatched:
		entry = {
			"employee": row.get("employee"),
			"time": row["time"],
			"log_type": row["log_type"],
			"remote_name": row.get("name"),
			"device_id": row.get("device_id"),
			"past_midnight": is_past_midnight(row["log_type"], row["time"]),
		}
		leftovers = local_at_moment.get((row.get("employee"), row["time"])) or []
		if leftovers:
			other = leftovers.pop(0)
			type_mismatch.append({**entry, "local_log_type": other["log_type"], "local_name": other["name"]})
		else:
			missing.append(entry)

	return {"matched": matched, "missing": missing, "type_mismatch": type_mismatch}


def resolve_window(from_date, to_date, today: date) -> tuple[date, date]:
	"""(from, to), inclusive. Defaults to the last 14 days; refuses > MAX_WINDOW_DAYS."""
	end = _to_date(to_date) if to_date else today
	start = _to_date(from_date) if from_date else end - timedelta(days=DEFAULT_WINDOW_DAYS - 1)
	if start > end:
		raise ValueError(f"from_date {start} is after to_date {end}")
	days = (end - start).days + 1
	if days > MAX_WINDOW_DAYS:
		raise ValueError(
			f"window of {days} days is over the {MAX_WINDOW_DAYS}-day cap; run it in smaller windows"
		)
	return start, end


def _sample_row(entry: dict, employee_names: dict) -> dict:
	row = {
		"employee": entry["employee"],
		"employee_name": employee_names.get(entry["employee"]),
		"time": entry["time"].strftime("%Y-%m-%d %H:%M:%S"),
		"log_type": entry["log_type"],
		"remote_name": entry["remote_name"],
		"device_id": entry.get("device_id"),
		"past_midnight": entry["past_midnight"],
	}
	if "local_log_type" in entry:
		row.update(local_log_type=entry["local_log_type"], local_name=entry["local_name"])
	return row


def build_report(instance, window, remote_rows, local_rows, employee_names: dict, sample: int = 50) -> dict:
	"""The report dict. Pure. `employee_names` maps every local Employee to its name."""
	mapped, unmapped = [], Counter()
	for row in remote_rows:
		if row.get("employee") in employee_names:
			mapped.append(row)
		else:
			unmapped[row.get("employee")] += 1

	diff = diff_punches(mapped, local_rows)
	return {
		"instance": instance,
		"window": {"from_date": window[0].isoformat(), "to_date": window[1].isoformat()},
		"remote_rows": len(remote_rows),
		"local_rows": len(local_rows),
		"matched": diff["matched"],
		"missing": len(diff["missing"]),
		"type_mismatch": len(diff["type_mismatch"]),
		"unmapped_employees": [
			{"employee": employee, "remote_punches": count} for employee, count in sorted(unmapped.items())
		],
		"by_employee": dict(sorted(Counter(entry["employee"] for entry in diff["missing"]).items())),
		"sample": [_sample_row(entry, employee_names) for entry in diff["missing"][:sample]],
		"type_mismatch_sample": [
			_sample_row(entry, employee_names) for entry in diff["type_mismatch"][:sample]
		],
	}


# --- reads ----------------------------------------------------------------------


def fetch_remote_punches(client, window, employees, split=None) -> list[dict]:
	"""Source punches whose TIME falls in the window (not `modified`).

	`employees` None reads every punch in the window; a list scopes the read and
	is split like the sync's own requests so the GET line stays short.
	"""
	if employees is not None and not employees:
		return []
	if split is None:
		from hrms.sync.runner import _split_filters as split

	filters = {"time": ["between", [window[0].isoformat(), window[1].isoformat()]]}
	if employees is not None:
		filters["employee"] = ["in", list(employees)]

	rows = []
	for chunk in split(filters):
		rows.extend(
			client.get_list(DOCTYPE, filters=chunk, fields=REMOTE_FIELDS, limit=None, order_by="name asc")
		)
	return rows


def _resolve_instance(instance: str | None) -> str:
	if instance:
		return instance
	enabled = frappe.get_all("HRMS ERP Instance", filters={"enabled": 1}, pluck="name", order_by="name asc")
	if len(enabled) == 1:
		return enabled[0]
	if not enabled:
		frappe.throw(
			_("No enabled HRMS ERP Instance on this site, so there is no source ERP to compare with.")
		)
	frappe.throw(_("Several enabled HRMS ERP Instances ({0}): pass instance=").format(", ".join(enabled)))


def _remote_scope(client, instance: str, employee: str | None) -> list[str] | None:
	"""Which source employees to read: the one asked for, the served companies' staff, or all."""
	if employee:
		return [employee]
	from hrms.sync.runner import instance_companies

	companies = instance_companies(instance)
	if not companies:
		return None  # unmapped instance: the sync pulls everything, so does this
	# Every status, Left included: a leaver's last punches are still punches.
	rows = client.get_list("Employee", filters={"company": ["in", companies]}, fields=["name"], limit=None)
	return [row["name"] for row in rows]


@frappe.whitelist()
def report(instance: str | None = None, from_date=None, to_date=None, employee=None, sample=50) -> dict:
	"""Source punches in [from_date, to_date] that are not on this hub. Read-only."""
	frappe.only_for(("System Manager", "HR Manager"))
	from hrms.overrides.company_scope import require_unfenced

	require_unfenced(_("compare punches across the whole source instance"))

	from frappe.utils import cint, getdate

	from hrms.sync.client import RemoteInstanceClient, RemoteInstanceError

	sample = min(max(cint(sample), 0), MAX_SAMPLE)
	try:
		window = resolve_window(from_date, to_date, getdate())
	except ValueError as e:
		frappe.throw(str(e))

	instance = _resolve_instance(instance)
	local_filters = {"employee": employee} if employee else {}
	employee_names = {
		row.name: row.employee_name
		for row in frappe.get_all("Employee", filters=local_filters, fields=["name", "employee_name"])
	}

	try:
		client = RemoteInstanceClient(instance)
		scope = _remote_scope(client, instance, employee)
		remote_rows = fetch_remote_punches(client, window, scope)
	except RemoteInstanceError as e:
		logger.warning("[missing_checkins] cannot read source %s: %s", instance, e)
		frappe.throw(_("Cannot read punches from {0}: {1}").format(instance, e))

	local_rows = frappe.get_all(
		DOCTYPE,
		filters={
			**local_filters,
			"time": [
				"between",
				[(window[0] - LOCAL_SLACK).isoformat(), (window[1] + LOCAL_SLACK).isoformat()],
			],
		},
		fields=LOCAL_FIELDS,
		order_by="time asc",
	)

	result = build_report(instance, window, remote_rows, local_rows, employee_names, sample=sample)
	result["unlocked"] = bool(frappe.db.get_value("HRMS ERP Instance", instance, "unlock_mirrored_writes"))
	logger.info(
		"[missing_checkins] %s %s..%s: remote=%s local=%s missing=%s type_mismatch=%s unmapped=%s",
		instance,
		result["window"]["from_date"],
		result["window"]["to_date"],
		result["remote_rows"],
		result["local_rows"],
		result["missing"],
		result["type_mismatch"],
		len(result["unmapped_employees"]),
	)
	return result
