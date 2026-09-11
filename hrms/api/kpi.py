# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import logging

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from hrms.utils.identity import require_employee

logger = logging.getLogger(__name__)

KRA_ROW_FIELDS = (
	"kra",
	"kpi",
	"kra_category",
	"per_weightage",
	"target",
	"actual",
	"achievement",
	"manager_rating",
	"weighted_score",
	"goal_completion",
	"goal_score",
)

# Sentinel cycle value meaning "average across every cycle of the year".
ALL_CYCLES = "_all"


def _get_session_employee() -> str:
	return require_employee()


def _get_cycle_dates(cycle_names) -> dict:
	"""Map each Appraisal Cycle to its end (or start) date, used to backfill the
	period for appraisals whose own start/end dates are empty — e.g. the NHSB
	flow populates only `performance_period` and the cycle, not the date fields."""
	if not cycle_names:
		return {}
	rows = frappe.get_all(
		"Appraisal Cycle",
		filters={"name": ("in", list(cycle_names))},
		fields=["name", "start_date", "end_date"],
	)
	logger.info("[kpi] resolved dates for %d appraisal cycle(s)", len(rows))
	return {row.name: (row.end_date or row.start_date) for row in rows}


def _effective_appraisal_date(appraisal, cycle_dates):
	"""Best available date for year-grouping. Never returns None, so an appraisal
	is never dropped for a missing end_date: own end/start → cycle → creation."""
	cyc = cycle_dates.get(appraisal.appraisal_cycle)
	raw = appraisal.end_date or appraisal.start_date or cyc or appraisal.creation
	return getdate(raw)


def _bar_percent(row) -> float:
	"""Single progress metric for a KRA row, mirroring the PWA bar logic:
	achievement/goal rows carry a percentage, manual rows a 1-5 rating."""
	return flt(row.achievement) or flt(row.goal_completion) or flt(row.manager_rating) / 5 * 100


def _year_average(year_appraisals, year: int) -> dict:
	"""Synthetic "current" block averaging every appraisal cycle of the year.

	KRA rows are grouped by (KRA, KPI) so each distinct KPI stays its own row and
	is averaged across cycles — grouping by KRA name alone collapsed sibling KPIs
	(e.g. the three "Product Presence" KPIs) into one row, which no longer matched
	the single-cycle view. target/actual are averaged too (numeric KPIs).
	"""
	docs = []
	for a in year_appraisals:
		doc = frappe.get_doc("Appraisal", a.name)
		# Defense in depth: the own-employee rule in Appraisal.has_permission
		# must allow this read; fail loudly if the visibility scope ever changes.
		frappe.has_permission("Appraisal", doc=doc, throw=True)
		docs.append(doc)

	grouped = {}
	for doc in docs:
		for row in doc.appraisal_kra:
			group = grouped.setdefault(
				(row.kra, row.kpi),
				{
					"kra": row.kra,
					"kpi": row.kpi,
					"kra_category": row.kra_category,
					"weightages": [],
					"percents": [],
					"weighted_scores": [],
					"targets": [],
					"actuals": [],
				},
			)
			group["weightages"].append(flt(row.per_weightage))
			group["percents"].append(_bar_percent(row))
			group["weighted_scores"].append(flt(row.weighted_score))
			group["targets"].append(flt(row.target))
			group["actuals"].append(flt(row.actual))

	def avg(values):
		return sum(values) / len(values) if values else 0.0

	kras = [
		{
			"kra": group["kra"],
			"kpi": group["kpi"],
			"kra_category": group["kra_category"],
			"per_weightage": avg(group["weightages"]),
			# averaged bar percentage rides in `achievement` so the PWA's
			# existing bar logic renders it without a special case
			"achievement": avg(group["percents"]),
			"weighted_score": avg(group["weighted_scores"]),
			"target": avg(group["targets"]),
			"actual": avg(group["actuals"]),
			"cycles": len(group["percents"]),
		}
		for group in grouped.values()
	]

	logger.info("[kpi] year-average year=%s cycles=%d kras=%d", year, len(docs), len(kras))

	return {
		"appraisal": None,
		"cycle": str(year),
		"is_average": True,
		"cycles_count": len(docs),
		"total_score": avg([flt(doc.pms_total_score) for doc in docs]),
		"grade": None,
		"docstatus": None,
		"kras": kras,
	}


@frappe.whitelist()
def get_my_kpi_dashboard(year: str | int | None = None, cycle: str | None = None) -> dict:
	"""Personal KRA/KPI dashboard for the logged-in employee (PWA "My KPI").

	Deliberately takes no employee argument: the appraisal visibility hooks in
	appraisal.py do not cover whitelisted endpoints, so this endpoint is
	scoped to the session user's own Employee by construction.

	year: calendar year of the appraisal's effective date (its end/start date, or
	its cycle's, or its creation date); defaults to the latest.
	cycle: an Appraisal Cycle name within that year, or ALL_CYCLES ("_all")
	to average across every cycle of the year; defaults to the latest cycle.
	"""
	employee = _get_session_employee()
	emp = frappe.db.get_value(
		"Employee", employee, ["name", "employee_name", "designation", "image"], as_dict=True
	)

	appraisals = frappe.get_all(
		"Appraisal",
		filters={"employee": employee, "docstatus": ("<", 2)},
		fields=[
			"name",
			"appraisal_cycle",
			"start_date",
			"end_date",
			"pms_total_score",
			"overall_grade",
			"docstatus",
			"creation",
		],
		order_by="modified desc",
	)

	# Resolve each appraisal's effective date and order newest-first by it. Custom
	# appraisals (NHSB) can leave start_date/end_date empty and keep the period only
	# on the cycle, so grouping on end_date alone silently dropped them and blanked
	# My KPI (v15.94.0 regression). _effective_appraisal_date never returns None.
	cycle_dates = _get_cycle_dates({a.appraisal_cycle for a in appraisals if a.appraisal_cycle})
	for a in appraisals:
		a.effective_date = _effective_appraisal_date(a, cycle_dates)
	appraisals.sort(key=lambda a: a.effective_date, reverse=True)

	years = sorted({a.effective_date.year for a in appraisals}, reverse=True)
	selected_year = cint(year) if year else (years[0] if years else None)
	year_appraisals = [a for a in appraisals if a.effective_date.year == selected_year]
	cycles = list(dict.fromkeys(a.appraisal_cycle for a in year_appraisals))

	logger.info(
		"[kpi] dashboard user=%s employee=%s appraisals=%d year=%s cycle=%s",
		frappe.session.user,
		employee,
		len(appraisals),
		selected_year,
		cycle,
	)

	if not year_appraisals:
		return {
			"employee": emp,
			"current": None,
			"previous_score": None,
			"history": [],
			"feedback": {"count": 0},
			"years": years,
			"cycles": cycles,
			"selected_year": selected_year,
			"selected_cycle": None,
		}

	trend = [
		{
			"appraisal": a.name,
			"cycle": a.appraisal_cycle,
			"end_date": a.end_date or a.effective_date,
			"total_score": flt(a.pms_total_score),
			"grade": a.overall_grade,
		}
		for a in reversed(year_appraisals)
	]

	if cycle == ALL_CYCLES:
		current = _year_average(year_appraisals, selected_year)
		selected_cycle = ALL_CYCLES
		previous_score = None
		feedback_count = frappe.db.count(
			"Employee Performance Feedback",
			{"employee": employee, "appraisal": ("in", [a.name for a in year_appraisals])},
		)
	else:
		selected = next((a for a in year_appraisals if a.appraisal_cycle == cycle), year_appraisals[0])
		doc = frappe.get_doc("Appraisal", selected.name)
		# Defense in depth: the own-employee rule in Appraisal.has_permission
		# must allow this read; fail loudly if the visibility scope ever changes.
		frappe.has_permission("Appraisal", doc=doc, throw=True)

		kras = [{field: row.get(field) for field in KRA_ROW_FIELDS} for row in doc.appraisal_kra]

		current = {
			"appraisal": doc.name,
			"cycle": doc.appraisal_cycle,
			"start_date": doc.start_date,
			"end_date": doc.end_date,
			"total_score": flt(doc.pms_total_score),
			"grade": doc.overall_grade,
			"docstatus": doc.docstatus,
			"section_scores": {
				"a1": flt(doc.a1_score),
				"a2": flt(doc.a2_score),
				"section_a": flt(doc.section_a_score),
				"section_b": flt(doc.section_b_score),
				"section_c": flt(doc.section_c_score),
			},
			"self_score": flt(doc.self_score),
			"avg_feedback_score": flt(doc.avg_feedback_score),
			"kras": kras,
		}
		selected_cycle = doc.appraisal_cycle

		selected_index = next(i for i, a in enumerate(appraisals) if a.name == selected.name)
		previous_score = next(
			(flt(a.pms_total_score) for a in appraisals[selected_index + 1 :] if a.docstatus == 1),
			None,
		)
		feedback_count = frappe.db.count(
			"Employee Performance Feedback", {"employee": employee, "appraisal": doc.name}
		)

	return {
		"employee": emp,
		"current": current,
		"previous_score": previous_score,
		"history": trend,
		"feedback": {"count": feedback_count},
		"years": years,
		"cycles": cycles,
		"selected_year": selected_year,
		"selected_cycle": selected_cycle,
	}


#: The one designation that may read the Team KPI view. This is deliberately a
#: designation and NOT a role: the request was "the CEO sees this", and roles on
#: this hub are bundled into role profiles (an approver profile also carries HR
#: roles), so a role gate would have handed the view to every HR user. The
#: Employee master is the register of who holds the office; nothing else is.
CEO_DESIGNATION = "Chief Executive Officer"


def _ceo_employee() -> dict | None:
	"""The session's Employee row when — and only when — it carries the CEO
	designation. Returns None for everyone else, including Administrator: the
	framework identity is not a person and holds no office."""
	employee = frappe.db.get_value(
		"Employee",
		{"user_id": frappe.session.user, "status": "Active"},
		["name", "employee_name", "designation", "company"],
		as_dict=True,
	)
	if not employee or employee.designation != CEO_DESIGNATION:
		return None
	return employee


def _require_ceo() -> dict:
	employee = _ceo_employee()
	if not employee:
		logger.warning(
			"[kpi] team view refused for user=%s (designation gate: %s)",
			frappe.session.user,
			CEO_DESIGNATION,
		)
		frappe.throw(
			_("The Team KPI view is available to the Chief Executive Officer."), frappe.PermissionError
		)
	return employee


@frappe.whitelist()
def can_view_team_kpi() -> bool:
	"""Nav/tab gate for the PWA. Cheap, cached per user, and says nothing about
	the data itself — every read re-checks through _require_ceo."""
	allowed = _ceo_employee() is not None
	logger.info("[kpi] can_view_team_kpi user=%s -> %s", frappe.session.user, allowed)
	return allowed


@frappe.whitelist()
def get_team_kpi(
	year: str | int | None = None, cycle: str | None = None, department: str | None = None
) -> dict:
	"""Read-only appraisal scores across the CEO's company, grouped by department.

	Scope is the CEO's own Employee.company — on a multi-company hub the office
	is held per company, so a hub-wide read would leak sideways. Rows carry one
	score per employee: the selected cycle's, or the mean of the year's cycles
	when `cycle` is ALL_CYCLES (the default, matching My KPI's year view).

	There is no write counterpart and no employee argument that selects someone
	to act on — this endpoint only reports.
	"""
	ceo = _require_ceo()

	appraisals = frappe.get_all(
		"Appraisal",
		filters={"company": ceo.company, "docstatus": ("<", 2)},
		fields=[
			"name",
			"employee",
			"employee_name",
			"appraisal_cycle",
			"start_date",
			"end_date",
			"pms_total_score",
			"overall_grade",
			"creation",
		],
	)

	cycle_dates = _get_cycle_dates({a.appraisal_cycle for a in appraisals if a.appraisal_cycle})
	for a in appraisals:
		a.effective_date = _effective_appraisal_date(a, cycle_dates)

	years = sorted({a.effective_date.year for a in appraisals}, reverse=True)
	selected_year = cint(year) if year else (years[0] if years else None)
	in_year = [a for a in appraisals if a.effective_date.year == selected_year]
	in_year.sort(key=lambda a: a.effective_date, reverse=True)
	cycles = list(dict.fromkeys(a.appraisal_cycle for a in in_year))

	# One lookup for every employee in play, so the row list costs two queries
	# regardless of headcount.
	employee_names = {a.employee for a in in_year}
	employees = {
		row.name: row
		for row in frappe.get_all(
			"Employee",
			filters={"name": ("in", list(employee_names))} if employee_names else {"name": ("in", [""])},
			fields=["name", "employee_name", "designation", "department", "image"],
		)
	}

	# Departments offered are those that actually have an appraisal this year —
	# a selector listing empty departments reads as broken data.
	departments = sorted(
		{employees[e].department for e in employee_names if employees.get(e) and employees[e].department}
	)

	selected_cycle = cycle or ALL_CYCLES
	if selected_cycle != ALL_CYCLES:
		in_year = [a for a in in_year if a.appraisal_cycle == selected_cycle]

	grouped: dict[str, dict] = {}
	for a in in_year:
		emp = employees.get(a.employee)
		if not emp:
			continue
		if department and emp.department != department:
			continue
		group = grouped.setdefault(
			a.employee,
			{
				"employee": a.employee,
				"employee_name": a.employee_name or emp.employee_name,
				"designation": emp.designation,
				"department": emp.department,
				"image": emp.image,
				"appraisal": a.name,
				"cycle": a.appraisal_cycle,
				"grade": a.overall_grade,
				"_scores": [],
			},
		)
		group["_scores"].append(flt(a.pms_total_score))

	rows = []
	for group in grouped.values():
		scores = group.pop("_scores")
		group["total_score"] = sum(scores) / len(scores) if scores else 0.0
		group["cycles_count"] = len(scores)
		if len(scores) > 1:
			# an average is not any one cycle's grade
			group["grade"] = None
			group["appraisal"] = None
		rows.append(group)
	rows.sort(key=lambda r: r["total_score"], reverse=True)

	average = sum(r["total_score"] for r in rows) / len(rows) if rows else 0.0
	logger.info(
		"[kpi] team view ceo=%s company=%s year=%s cycle=%s department=%s rows=%d",
		ceo.name,
		ceo.company,
		selected_year,
		selected_cycle,
		department,
		len(rows),
	)

	return {
		"company": ceo.company,
		"departments": departments,
		"selected_department": department or None,
		"years": years,
		"cycles": cycles,
		"selected_year": selected_year,
		"selected_cycle": selected_cycle,
		"summary": {
			"headcount": len(rows),
			"average_score": average,
			"top_score": rows[0]["total_score"] if rows else 0.0,
		},
		"rows": rows,
	}
