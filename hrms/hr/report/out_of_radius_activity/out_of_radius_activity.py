"""Out of Radius Activity — script report.

Unions two sources to give HR one view of every out-of-geofence check-in
event in the period:

  1. `Remote Checkin Request` rows — lenient-mode shifts where the user
     was outside the radius and triggered the remote-approval flow. Status
     mapped to Pending / Approved / Rejected.

  2. `Geofence Reject Log` rows — strict-mode shifts where the user was
     blocked outright (status: Blocked) or the shift was misconfigured
     (status: Misconfig).

Filters (sidebar):
  - from_date, to_date (default: last 7 days inclusive)
  - employee (Link Employee, optional)
  - shift_type (Link Shift Type, optional)
  - shift_location (Link Shift Location, optional)
  - status (Multi-select via Select with "All" sentinel) — filter the
    union AFTER both queries have been normalised.
"""

from __future__ import annotations

import logging
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import add_days, getdate

logger = logging.getLogger(__name__)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	_apply_default_dates(filters)
	logger.info("[out_of_radius_activity] execute filters=%s", dict(filters))

	rows = _fetch_remote_requests(filters) + _fetch_reject_logs(filters)
	rows = _apply_status_filter(rows, filters.get("status"))
	rows.sort(key=lambda r: r.get("event_time") or "", reverse=True)
	logger.info("[out_of_radius_activity] returning %d rows", len(rows))
	return _columns(), rows


def _apply_default_dates(filters):
	if not filters.get("to_date"):
		filters["to_date"] = frappe.utils.today()
	if not filters.get("from_date"):
		filters["from_date"] = add_days(filters["to_date"], -6)


def _columns():
	return [
		{
			"fieldname": "event_time",
			"label": _("Time"),
			"fieldtype": "Datetime",
			"width": 150,
		},
		{
			"fieldname": "employee",
			"label": _("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 130,
		},
		{
			"fieldname": "employee_name",
			"label": _("Name"),
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"fieldname": "log_type",
			"label": _("Type"),
			"fieldtype": "Data",
			"width": 60,
		},
		{
			"fieldname": "shift_type",
			"label": _("Shift"),
			"fieldtype": "Link",
			"options": "Shift Type",
			"width": 150,
		},
		{
			"fieldname": "shift_location",
			"label": _("Shift Location"),
			"fieldtype": "Link",
			"options": "Shift Location",
			"width": 150,
		},
		{
			"fieldname": "distance_m",
			"label": _("Distance (m)"),
			"fieldtype": "Float",
			"precision": 1,
			"width": 100,
		},
		{
			"fieldname": "radius_m",
			"label": _("Radius (m)"),
			"fieldtype": "Int",
			"width": 90,
		},
		{
			"fieldname": "overshoot_m",
			"label": _("Overshoot (m)"),
			"fieldtype": "Float",
			"precision": 1,
			"width": 110,
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"fieldname": "reason",
			"label": _("Reason"),
			"fieldtype": "Small Text",
			"width": 220,
		},
		{
			"fieldname": "reference",
			"label": _("Reference"),
			"fieldtype": "Dynamic Link",
			"options": "reference_doctype",
			"width": 180,
		},
		{
			"fieldname": "reference_doctype",
			"label": _("Doctype"),
			"fieldtype": "Data",
			"width": 0,
			"hidden": 1,
		},
	]


def _fetch_remote_requests(filters):
	conditions = ["docstatus < 2", "checkin_time BETWEEN %(from)s AND %(to)s"]
	params = {
		"from": f"{filters['from_date']} 00:00:00",
		"to": f"{filters['to_date']} 23:59:59",
	}
	if filters.get("employee"):
		conditions.append("employee = %(employee)s")
		params["employee"] = filters["employee"]
	if filters.get("shift_location"):
		conditions.append("nearest_shift_location = %(shift_location)s")
		params["shift_location"] = filters["shift_location"]

	rows = frappe.db.sql(
		f"""
		SELECT
		    rcr.name, rcr.employee, rcr.checkin_time, rcr.log_type,
		    rcr.distance_m, rcr.status, rcr.nearest_shift_location,
		    rcr.employee_remarks, ec.shift AS shift_type
		FROM `tabRemote Checkin Request` rcr
		LEFT JOIN `tabEmployee Checkin` ec ON ec.name = rcr.checkin
		WHERE {" AND ".join(conditions)}
		""",
		params,
		as_dict=True,
	)

	if filters.get("shift_type"):
		rows = [r for r in rows if r.get("shift_type") == filters["shift_type"]]

	out = []
	for r in rows:
		out.append(
			{
				"event_time": r.checkin_time,
				"employee": r.employee,
				"employee_name": _resolve_employee_name(r.employee),
				"log_type": r.log_type,
				"shift_type": r.shift_type,
				"shift_location": r.nearest_shift_location,
				"distance_m": r.distance_m,
				"radius_m": None,
				"overshoot_m": r.distance_m,
				"status": r.status or "Pending",
				"reason": (r.employee_remarks or "").strip()[:200] or _("Remote check-in"),
				"reference_doctype": "Remote Checkin Request",
				"reference": r.name,
			}
		)
	return out


def _fetch_reject_logs(filters):
	conditions = ["rejected_at BETWEEN %(from)s AND %(to)s"]
	params = {
		"from": f"{filters['from_date']} 00:00:00",
		"to": f"{filters['to_date']} 23:59:59",
	}
	for key in ("employee", "shift_type", "shift_location"):
		if filters.get(key):
			conditions.append(f"{key} = %({key})s")
			params[key] = filters[key]

	rows = frappe.db.sql(
		f"""
		SELECT name, employee, employee_name, log_type, rejected_at,
		       shift_type, shift_location, reason,
		       distance_m, radius_m, overshoot_m
		FROM `tabGeofence Reject Log`
		WHERE {" AND ".join(conditions)}
		""",
		params,
		as_dict=True,
	)

	out = []
	for r in rows:
		out.append(
			{
				"event_time": r.rejected_at,
				"employee": r.employee,
				"employee_name": r.employee_name,
				"log_type": r.log_type,
				"shift_type": r.shift_type,
				"shift_location": r.shift_location,
				"distance_m": r.distance_m,
				"radius_m": r.radius_m,
				"overshoot_m": r.overshoot_m,
				"status": "Misconfig" if r.reason in ("no_shift_location", "no_radius") else "Blocked",
				"reason": _reason_label(r.reason),
				"reference_doctype": "Geofence Reject Log",
				"reference": r.name,
			}
		)
	return out


def _reason_label(reason):
	return {
		"outside_radius": _("Outside radius (strict mode)"),
		"no_shift_location": _("Strict mode but assignment missing Shift Location"),
		"no_radius": _("Strict mode but Shift Location has no radius"),
	}.get(reason, reason or "")


def _apply_status_filter(rows, status):
	if not status or status == "All":
		return rows
	return [r for r in rows if r.get("status") == status]


_NAME_CACHE: dict[str, str] = {}


def _resolve_employee_name(employee_id):
	if not employee_id:
		return ""
	cached = _NAME_CACHE.get(employee_id)
	if cached is not None:
		return cached
	value = frappe.db.get_value("Employee", employee_id, "employee_name") or ""
	_NAME_CACHE[employee_id] = value
	return value
