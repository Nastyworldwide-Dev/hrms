# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import logging

import frappe
from frappe import _
from frappe.utils import flt

logger = logging.getLogger(__name__)

HR_REPORT_ROLES = ("System Manager", "HR Manager", "HR User")

# Rating fields store 0..1; the UI shows 5 stars
RATING_SCALE = 5


def execute(filters=None):
	_check_access()
	filters = frappe._dict(filters or {})

	expected = _get_expected_by_designation(filters)
	averages = _get_average_proficiencies(filters)

	designations = sorted(set(expected) | set(averages))
	skills = sorted({s for m in expected.values() for s in m} | {s for m in averages.values() for s in m})
	logger.info(
		"[skills_gap] user=%s designations=%d skills=%d",
		frappe.session.user,
		len(designations),
		len(skills),
	)

	columns = [
		{
			"fieldname": "designation",
			"label": _("Designation"),
			"fieldtype": "Link",
			"options": "Designation",
			"width": 200,
		}
	]
	for skill in skills:
		columns.append(
			{
				"fieldname": frappe.scrub(skill),
				"label": skill,
				"fieldtype": "Data",
				"width": 140,
			}
		)

	data = []
	for designation in designations:
		row = {"designation": designation}
		for skill in skills:
			avg = averages.get(designation, {}).get(skill)
			target = expected.get(designation, {}).get(skill)
			row[frappe.scrub(skill)] = _format_cell(avg, target)
		data.append(row)

	return columns, data


def _check_access():
	"""Report roles cover desk access, but script reports can also be run via
	API — keep the guard explicit like the appraisal report guards."""
	user = frappe.session.user
	if user == "Administrator" or set(HR_REPORT_ROLES) & set(frappe.get_roles(user)):
		return
	frappe.throw(_("You are not permitted to view the Skills Gap Matrix."), frappe.PermissionError)


def _get_expected_by_designation(filters) -> dict[str, dict[str, float]]:
	rows = frappe.get_all(
		"Designation Skill",
		filters={"parenttype": "Designation"},
		fields=["parent", "skill", "expected_proficiency"],
	)
	expected: dict[str, dict[str, float]] = {}
	for row in rows:
		if filters.designation and row.parent != filters.designation:
			continue
		expected.setdefault(row.parent, {})[row.skill] = flt(row.expected_proficiency)
	return expected


def _get_average_proficiencies(filters) -> dict[str, dict[str, float]]:
	conditions = "emp.status = 'Active'"
	values = {}
	if filters.designation:
		conditions += " and esm.designation = %(designation)s"
		values["designation"] = filters.designation
	if filters.company:
		conditions += " and emp.company = %(company)s"
		values["company"] = filters.company

	rows = frappe.db.sql(
		f"""
		select esm.designation, es.skill, avg(es.proficiency) as avg_proficiency
		from `tabEmployee Skill` es
		inner join `tabEmployee Skill Map` esm on es.parent = esm.name
		inner join `tabEmployee` emp on esm.employee = emp.name
		where {conditions}
		group by esm.designation, es.skill
		""",
		values,
		as_dict=True,
	)
	averages: dict[str, dict[str, float]] = {}
	for row in rows:
		if not row.designation:
			continue
		averages.setdefault(row.designation, {})[row.skill] = flt(row.avg_proficiency)
	return averages


def _format_cell(avg: float | None, target: float | None) -> str:
	if avg is None and not target:
		return ""
	avg_stars = f"{flt(avg) * RATING_SCALE:.1f}" if avg is not None else "—"
	if not target:
		return avg_stars
	return f"{avg_stars} / {flt(target) * RATING_SCALE:.1f}"
