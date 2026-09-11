# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import logging

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from hrms.hr.utils import is_hr_operator
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
		# rounded for the same reason the team view rounds: GProgressRing prints
		# its score verbatim into an 88px circle and reads it out in full
		"total_score": flt(avg([flt(doc.pms_total_score) for doc in docs]), 1),
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


#: The designation that carries the first of Team KPI's two allowlists. This is
#: deliberately a designation and NOT a role: roles on this hub are bundled into
#: role profiles (the approver profile also carries the HR roles), so "the CEO"
#: is not expressible as a role at all. The Employee master is the register of
#: who holds the office; nothing else is.
CEO_DESIGNATION = "Chief Executive Officer"

#: The two ways in, reported back to the PWA for logging and support.
VIEWER_CEO = "ceo"
VIEWER_HR = "hr"


def _holds_the_office(user: str) -> bool:
	"""True when an Active Employee claiming this user carries the CEO
	designation. Compared case- and whitespace-insensitively: `designation` is a
	Link to a master people retype by hand, and an office is not lost to a
	trailing space."""
	designations = frappe.get_all(
		"Employee",
		filters={"user_id": user, "status": "Active"},
		pluck="designation",
	)
	target = CEO_DESIGNATION.strip().casefold()
	return any((d or "").strip().casefold() == target for d in designations)


def _team_kpi_viewer() -> str | None:
	"""Which of Team KPI's two allowlists lets this session read it, if either.

	TWO allowlists, different in kind and deliberately so:

	  ceo — by DESIGNATION (see CEO_DESIGNATION).
	  hr  — by ROLE, through `is_hr_operator`: the SAME predicate that already
	        governs every other HR-only surface here (the issue board, SOPs, the
	        full directory, the PWA's `is_hr` flag). Reusing it means Team KPI
	        can never drift from the rest of HR's sight, and a future policy
	        ruling moves both at once. It is HR User / HR Manager only —
	        System Manager is a technical role and confers nothing. Administrator
	        also satisfies it and is reported as `hr`; that is no escalation (it
	        already reads every Appraisal) but it does mean a support log line
	        saying "hr" may be the framework identity, not a person.

	NEITHER IS COMPANY-FENCED, and that is a deliberate ruling, not an omission.
	Team KPI is group-level sight by definition: HR sees every company, the CEO
	sees every company, and nobody else sees the page at all.

	This is the ONE place on the hub where an `allow=Company` User Permission —
	the fence behind the "HR (Company)" and "HR (Instance)" roles — does not
	narrow an HR user. Everywhere else (Employee rows, reports, the sync
	endpoints) it still does. Pinned by
	test_a_company_user_permission_does_not_narrow_team_kpi so the exception
	cannot be reintroduced or removed by accident; if the ruling changes, that
	test is the place it changes.
	"""
	user = frappe.session.user
	if _holds_the_office(user):
		return VIEWER_CEO
	if is_hr_operator(user):
		return VIEWER_HR
	return None


def _require_team_kpi_viewer() -> str:
	viewer = _team_kpi_viewer()
	if not viewer:
		logger.warning("[kpi] team view refused for user=%s", frappe.session.user)
		frappe.throw(
			_("The Team KPI view is available to the Chief Executive Officer and to HR."),
			frappe.PermissionError,
		)
	return viewer


@frappe.whitelist()
def can_view_team_kpi() -> bool:
	"""Nav/tab gate for the PWA. Cheap, cached per user, and says nothing about
	the data itself — every read re-checks through _require_team_kpi_viewer."""
	viewer = _team_kpi_viewer()
	logger.info("[kpi] can_view_team_kpi user=%s -> %s", frappe.session.user, viewer)
	return viewer is not None


@frappe.whitelist()
def get_team_kpi(
	year: str | int | None = None,
	cycle: str | None = None,
	department: str | None = None,
	company: str | None = None,
) -> dict:
	"""Read-only appraisal scores across EVERY company on the hub.

	Rows carry one score per employee: the selected cycle's, or the mean of the
	year's cycles when `cycle` is ALL_CYCLES (the default, matching My KPI's
	year view). `company` and `department` are presentation filters only — the
	audience for this page is group-level by definition (see
	_team_kpi_viewer), so there is nothing here for them to narrow past. A
	company that does not exist is refused rather than quietly emptied, because
	a silently empty table reads as "nobody was appraised".

	There is no write counterpart and no employee argument that selects someone
	to act on — this endpoint only reports.
	"""
	viewer = _require_team_kpi_viewer()

	if company and not frappe.db.exists("Company", company):
		# An empty table reads as "nobody was appraised", so a company that does
		# not exist has to say so rather than look like an answer.
		frappe.throw(_("No such company: {0}.").format(company))

	# Every employee on the hub. The audience for this page is group-level, so
	# there is no company predicate here — see _team_kpi_viewer for the ruling.
	# Exempted from the class guard with that reason in
	# hrms/tests/test_api_employee_reads_are_fenced.py::EXEMPT_REASONS.
	#
	# ceiling: whole-tabEmployee read, measured ~100 ms / ~15 MB at 25 000
	# employees (3 ms / 0.3 MB at 500)
	# upgrade: push the company and department predicates into SQL past ~25 000
	# employees, once the dict itself is the cost rather than the query
	#
	# What IS load-bearing: the row's company comes from the EMPLOYEE, never
	# from Appraisal.company. The latter is a plain Link copied from the
	# Appraisal Cycle (appraisal_cycle.create_appraisals_for_cycle), has no
	# fetch_from, and validate() never reconciles the two — so it names the
	# wrong company often enough that the Company filter, the selector and the
	# Company column would all disagree with the Employee master. The row is
	# about a person, so the person's company governs it.
	employees = {
		row.name: row
		for row in frappe.get_all(
			"Employee",
			fields=["name", "employee_name", "designation", "department", "company", "image"],
		)
	}

	appraisals = frappe.get_all(
		"Appraisal",
		filters={"docstatus": ("<", 2)},
		fields=[
			"name",
			"employee",
			"employee_name",
			"company",
			"appraisal_cycle",
			"start_date",
			"end_date",
			"pms_total_score",
			"overall_grade",
			"creation",
		],
	)

	# An appraisal whose Employee row is gone resolves to nothing downstream,
	# so drop it here rather than guard every use of the map.
	appraisals = [a for a in appraisals if a.employee in employees]

	cycle_dates = _get_cycle_dates({a.appraisal_cycle for a in appraisals if a.appraisal_cycle})
	for a in appraisals:
		a.effective_date = _effective_appraisal_date(a, cycle_dates)

	years = sorted({a.effective_date.year for a in appraisals}, reverse=True)
	selected_year = cint(year) if year else (years[0] if years else None)
	in_year = [a for a in appraisals if a.effective_date.year == selected_year]
	in_year.sort(key=lambda a: a.effective_date, reverse=True)
	cycles = list(dict.fromkeys(a.appraisal_cycle for a in in_year))

	# The company selector lists every company that HAS an appraisal this year —
	# it is NOT narrowed by `company`, or choosing one would empty the control
	# that did the choosing.
	companies = sorted({employees[a.employee].company for a in in_year if employees[a.employee].company})

	# `company` is presentation narrowing only, applied AFTER years/cycles/
	# companies are fixed: narrowing those too would strand the year the viewer
	# is already on. Departments do follow it, since a department carries its
	# company's suffix and could never match across one.
	if company:
		in_year = [a for a in in_year if employees[a.employee].company == company]

	departments = sorted(
		{employees[a.employee].department for a in in_year if employees[a.employee].department}
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
				"company": emp.company,
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
		# ONE rounded source for the ring, the hero and the table. An unrounded
		# mean (72.42857142857143) reached GProgressRing's centre label, which
		# prints its score verbatim into an 88px ring with no overflow clamp —
		# and read out the full float to a screen reader.
		group["total_score"] = flt(sum(scores) / len(scores), 1) if scores else 0.0
		group["cycles_count"] = len(scores)
		if len(scores) > 1:
			# An average belongs to no single cycle, so every field that names
			# one is cleared — `cycle` included. Leaving it set named whichever
			# cycle happened to be first and quietly misattributed the mean.
			group["grade"] = None
			group["appraisal"] = None
			group["cycle"] = None
		rows.append(group)
	rows.sort(key=lambda r: r["total_score"], reverse=True)

	average = flt(sum(r["total_score"] for r in rows) / len(rows), 1) if rows else 0.0
	logger.info(
		"[kpi] team view user=%s mode=%s year=%s cycle=%s company=%s department=%s rows=%d",
		frappe.session.user,
		viewer,
		selected_year,
		selected_cycle,
		company,
		department,
		len(rows),
	)

	return {
		"viewer_mode": viewer,
		"companies": companies,
		"selected_company": company or None,
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
