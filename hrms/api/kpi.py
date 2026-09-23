# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import logging

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from hrms.hr.doctype.appraisal.appraisal import get_allowed_appraisal_employees
from hrms.hr.utils import is_hr_operator
from hrms.utils.identity import own_employees, require_employee

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


def _year_average(year_appraisals, year: int, verify_appraisal_permission: bool = True) -> dict:
	"""Synthetic "current" block averaging every appraisal cycle of the year.

	KRA rows are grouped by (KRA, KPI) so each distinct KPI stays its own row and
	is averaged across cycles — grouping by KRA name alone collapsed sibling KPIs
	(e.g. the three "Product Presence" KPIs) into one row, which no longer matched
	the single-cycle view. target/actual are averaged too (numeric KPIs).
	"""
	docs = []
	for a in year_appraisals:
		doc = frappe.get_doc("Appraisal", a.name)
		if verify_appraisal_permission:
			# Defense in depth on the SELF path — see _kpi_dashboard for why the
			# team path cannot use it.
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


@frappe.whitelist(methods=["GET", "POST"])
def get_my_kpi_dashboard(year: str | int | None = None, cycle: str | None = None) -> dict:
	"""Personal KRA/KPI dashboard for the logged-in employee (PWA "My KPI").

	Deliberately takes no employee argument: the appraisal visibility hooks in
	appraisal.py do not cover whitelisted endpoints, so this endpoint is scoped
	to the session user's own Employee BY CONSTRUCTION. `get_employee_kpi` is
	the door that does take one, and it carries its own lock.

	year: calendar year of the appraisal's effective date (its end/start date, or
	its cycle's, or its creation date); defaults to the latest.
	cycle: an Appraisal Cycle name within that year, or ALL_CYCLES ("_all")
	to average across every cycle of the year; defaults to the latest cycle.
	"""
	return _kpi_dashboard(_get_session_employee(), year, cycle, verify_appraisal_permission=True)


def _appraiser_name(employee: str) -> str | None:
	"""Who scores this person, by name.

	TWO HOPS, because `reports_to` holds an Employee ID and there is no
	`reports_to_name` on Employee in this fork — guessed otherwise and the
	bench said so immediately. Their own record and their manager's name: no
	fence is widened, and a manager's name is already on every request this
	employee files.
	"""
	manager = frappe.db.get_value("Employee", employee, "reports_to")
	if not manager:
		return None
	return frappe.db.get_value("Employee", manager, "employee_name")


def _whats_next_for(employee: str) -> dict | None:
	"""What an employee with no appraisal should be told instead of nothing.

	The Score screen's empty state was a dashed box in a field of black. The
	question it left unanswered is the only one an employee actually has:
	"am I late for something?" A box saying "No appraisals yet" does not answer
	it, so people ask HR, and HR asks us.

	THE FENCE (revamp KR3): everything returned here is about the READER'S OWN
	cycle. An Appraisal Cycle is org-level configuration, not a person's data,
	and membership is checked against THIS employee's own row in `appraisees`.
	No other employee's name, score or appraisal is read, and nothing here
	widens `_scope` — it is a different question ("when does mine open") asked
	of the same fenced caller.

	Returns None when there is genuinely nothing scheduled, which is itself an
	answer the screen can state plainly.
	"""
	rows = frappe.get_all(
		"Appraisal Cycle",
		filters={"status": ("in", ("Not Started", "In Progress"))},
		fields=["name", "cycle_name", "start_date", "end_date", "status"],
		order_by="start_date asc",
	)
	for row in rows:
		# Membership, not visibility: an employee is IN a cycle when the cycle
		# lists them. Checked per cycle rather than by joining, because the
		# child table is small and a join here would read other appraisees.
		if not frappe.db.exists("Appraisee", {"parent": row.name, "employee": employee}):
			continue
		logger.info("[kpi] whats-next employee=%s cycle=%s status=%s", employee, row.name, row.status)
		return {
			"cycle": row.name,
			"cycle_name": row.cycle_name or row.name,
			"start_date": row.start_date,
			"end_date": row.end_date,
			"status": row.status,
			# "Who scores me" is the second question after "when" — the plan
			# names it, and it costs one field of the employee's own record.
			"appraiser": _appraiser_name(employee),
		}
	# NO CYCLE INCLUDES THIS EMPLOYEE. That is still an answer, and the honest
	# one — but the screen had nothing to render and fell back to a dashed box
	# in a field of black, which is what the owner photographed on 23 September.
	#
	# So say WHO to ask. An employee whose review has not been scheduled cannot
	# fix that themselves; what they need is the name of the person who can,
	# and their own appraiser is the right one. Read from the Employee record —
	# it is their own row, so no fence is widened.
	logger.info("[kpi] whats-next employee=%s — no scheduled cycle", employee)
	return {
		"cycle": None,
		"cycle_name": None,
		"start_date": None,
		"end_date": None,
		"status": None,
		# The only actionable fact available when nothing is scheduled.
		"appraiser": _appraiser_name(employee),
	}


def _kpi_dashboard(
	employee: str,
	year: str | int | None,
	cycle: str | None,
	*,
	verify_appraisal_permission: bool,
) -> dict:
	"""The renderer. ONE payload shape, because the drill-down IS the My KPI
	layout pointed at somebody else — two shapes would half-render it.

	`verify_appraisal_permission` runs frappe.has_permission on each Appraisal
	as defense in depth. True on the SELF path, where it catches a drift in the
	own-employee rule. False on the team path, and deliberately: the CEO tier is
	granted by DESIGNATION, which appraisal.py's hook has never heard of — it
	admits Administrator, HR roles and the reporting chain only. Running it
	there would refuse the CEO their own feature, and silencing it per-caller
	would be worse than not calling it. On that path the tier fence in
	`_require_kpi_read` is the authority, and it is checked before a row is read.
	"""
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
		# An empty payload is still an ANSWER, and until 22 Sep 2026 it was not:
		# the screen drew a dashed box and left the reader to guess whether they
		# were late for something. `whats_next` is about this employee's own
		# cycle only (see _whats_next_for) and is None when nothing is scheduled,
		# which the screen states rather than hides.
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
			"whats_next": _whats_next_for(employee),
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
		current = _year_average(year_appraisals, selected_year, verify_appraisal_permission)
		selected_cycle = ALL_CYCLES
		previous_score = None
		feedback_count = frappe.db.count(
			"Employee Performance Feedback",
			{"employee": employee, "appraisal": ("in", [a.name for a in year_appraisals])},
		)
	else:
		selected = next((a for a in year_appraisals if a.appraisal_cycle == cycle), year_appraisals[0])
		doc = frappe.get_doc("Appraisal", selected.name)
		if verify_appraisal_permission:
			# Defense in depth on the SELF path: the own-employee rule in
			# Appraisal.has_permission must allow this read; fail loudly if the
			# visibility scope ever changes.
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

#: The three ways in, reported back to the PWA so it can label the tab and so
#: a support log says which tier answered.
VIEWER_CEO = "ceo"
VIEWER_HR = "hr"
VIEWER_MANAGER = "manager"
#: Not a tier — the answer when you are reading your OWN record. A bare literal
#: compared in two places is the same fragility that broke the tab trigger.
VIEWER_SELF = "self"


def _scope(user: str | None = None) -> tuple[str | None, list[str] | None]:
	"""(tier, the employees it admits). `None` admitted means unrestricted.

	THE ONE PLACE that answers "who is this caller, and whose rows may they
	see". It used to be three — the tier check, the detail fence and the list
	each recombined identity with the chain walk, with slightly different
	arithmetic. The difference cashed in as a real leak.

	IDENTITY FIRST, FOR EVERY TIER, and the chain walk SEEDED from it.
	`own_employees` is normalised, Active-only, and empty when a login is
	claimed twice. `appraisal._get_own_employees` — which the walk seeds from by
	default — is a raw, status-agnostic `user_id` match returning EVERY
	claimant. Subtracting the first from the second only closed the
	Active-vs-Active case: an Active row PLUS a leftover inactive row with
	subordinates still produced a phantom "manager" chain, and that caller could
	read the full KRA detail of people they manage nobody in — measured, while
	the framework's own has_permission refused them the very same document.

	The office is tested on the RESOLVED rows too. It used to run its own
	`user_id` query ahead of the gate, so the exact ambiguity this hub documents
	as fail-closed was handed the WIDEST tier.

	THE TIERS
	  ceo     — by DESIGNATION. Roles here are bundled into role profiles, so
	            "the CEO" is not expressible as a role at all; in Desk he holds
	            no HR role, which is the whole reason this tier exists.
	  hr      — by ROLE, through `is_hr_operator`: the SAME predicate that
	            governs every other HR-only surface here, so Team KPI can never
	            drift from the rest of HR's sight.
	  manager — by their reporting chain, borrowed from
	            `appraisal.get_allowed_appraisal_employees` rather than
	            re-derived. A manager could already read those appraisals in
	            Desk; this surfaces it, it does not grant it.
	The wider tier wins when somebody holds more than one.

	NEITHER CEO NOR HR IS COMPANY-FENCED, ANYWHERE ON THIS PAGE. Ruling (Nabil,
	11 Sep, restated 13 Sep 2026): HR manages the ENTIRE group and is not
	limited to a company — not for the list, and not for the personnel file
	behind it. So an `allow=Company` User Permission, including the one the
	"HR (Company)" role auto-provisions, does not narrow either tier here,
	and `get_employee_kpi` runs without the framework's appraisal check for
	them precisely because that check would re-impose the fence this ruling
	removes.

	This is the ONE place on the hub with that exemption; everywhere else the
	fence still binds. Pinned from the other side by
	test_a_company_user_permission_does_not_narrow_team_kpi and
	test_a_company_fenced_hr_still_opens_another_company_s_detail — if the
	ruling is ever reversed, those two are where it is reversed.
	"""
	user = user or frappe.session.user

	# HR IS DECIDED BY ROLE, AND ONLY BY ROLE, so it is answered before the
	# identity gate. Identity buys nothing here — a role cannot be forged with a
	# duplicate Employee row, and HR sees everyone regardless of any chain — but
	# requiring it would silently delete the tab from an HR account with no
	# Employee record: a new HR hire not yet mirrored, a shared HR login, or
	# Administrator during support. Losing the feature is the cost; there is no
	# matching security gain.
	if is_hr_operator(user):
		return VIEWER_HR, None

	# The other two tiers BOTH read Employee rows to decide themselves — the
	# office from a designation, the manager from a reporting chain — so for
	# them identity is the thing being decided and it goes first, fail-closed.
	own = own_employees(user)
	if not own:
		logger.info("[kpi] no single Active Employee for %s — no tier", user)
		return None, []

	designations = frappe.get_all("Employee", filters={"name": ("in", own)}, pluck="designation")
	target = CEO_DESIGNATION.strip().casefold()
	if any((d or "").strip().casefold() == target for d in designations):
		return VIEWER_CEO, None

	chain = get_allowed_appraisal_employees(user, seed=own) or []
	reports = [e for e in chain if e not in own]
	if reports:
		return VIEWER_MANAGER, reports
	return None, []


def _team_kpi_viewer() -> str | None:
	"""Which tier admits this session to the team view, if any. See `_scope`."""
	return _scope()[0]


@frappe.whitelist(methods=["GET", "POST"])
def can_view_team_kpi() -> str | None:
	"""Nav/tab gate for the PWA: the tier, or None. It says nothing about the
	data itself — every read re-checks through
	`_scope`.

	Returns the MODE rather than a bool so the tab can be labelled honestly:
	a manager's tab reads "My Team" and carries no company selector, because
	their scope is people, not structure. A falsy value still means no tab."""
	viewer = _team_kpi_viewer()
	logger.info("[kpi] can_view_team_kpi user=%s -> %s", frappe.session.user, viewer)
	return viewer


def _require_kpi_read(employee: str) -> str:
	"""May the caller open THIS person's KRA detail? Returns the tier that let
	them, or throws.

	The list view answers a different question — "whose rows may I see" — and a
	row there is a name and a number. This is the personnel file behind it: the
	manager's rating, the written feedback, every target and actual. So it gets
	its own check, and the check is the SAME tier the list already uses, never a
	second derivation. Two implementations of "may I see this person" is how the
	filing guard and the row scope came to disagree (.claude/plans/family.md).

	Checked BEFORE anything is read.
	"""
	# A whitelisted argument arrives as whatever the caller sent. A dict reaches
	# frappe.db.get_value as FILTERS rather than a name, so the argument is
	# narrowed to a string at the boundary before anything reads it. Only the
	# unrestricted tiers could reach that today — they already read everyone, so
	# it was not an escalation — but an untyped argument at a permission
	# boundary is a shape worth refusing, not a risk worth ranking.
	if not isinstance(employee, str) or not employee.strip():
		frappe.throw(_("An employee must be named."), frappe.PermissionError)
	employee = employee.strip()

	user = frappe.session.user
	if employee in own_employees(user):
		return VIEWER_SELF

	# ONE resolution, not a second derivation. `admitted` is None for the
	# unrestricted tiers and the manager's own chain otherwise — seeded from
	# identity, which is what closes the phantom-chain case.
	viewer, admitted = _scope(user)
	if viewer in (VIEWER_CEO, VIEWER_HR):
		return viewer
	if viewer == VIEWER_MANAGER and employee in (admitted or []):
		return viewer

	# The employee name is caller-supplied, so it is flattened before it reaches
	# the log: a newline in it forges log lines.
	logger.warning("[kpi] %s refused the KPI detail of %r (tier %s)", user, employee[:140], viewer)
	frappe.throw(_("You are not permitted to view this employee's KPI."), frappe.PermissionError)


@frappe.whitelist(methods=["GET", "POST"])
def get_employee_kpi(employee: str, year: str | int | None = None, cycle: str | None = None) -> dict:
	"""One person's KRA detail — the My KPI layout, pointed at somebody else.

	The only endpoint here that takes an employee, so it is the only one whose
	safety is by CHECK rather than by construction. `_require_kpi_read` runs
	first and throws before a single row is read.
	"""
	tier = _require_kpi_read(employee)
	logger.info("[kpi] %s opened the KPI detail of %s as %s", frappe.session.user, employee, tier)
	# The framework's appraisal check is kept wherever it can actually answer.
	# It says YES for a legitimate manager reading a report (measured), so
	# switching it off there bought nothing and cost a layer — it would have
	# caught the phantom-chain leak on this very door. It says NO for the CEO,
	# whose tier is by DESIGNATION, a thing appraisal.py has never heard of; and
	# for HR it re-imposes the company fence the ruling deliberately removes.
	return _kpi_dashboard(
		employee,
		year,
		cycle,
		verify_appraisal_permission=tier in (VIEWER_SELF, VIEWER_MANAGER),
	)


def _scored_rows(
	viewer: str,
	reports: list[str] | None,
	year: str | int | None,
	cycle: str | None,
	company: str | None,
	department: str | None,
) -> dict:
	"""The scoring pipeline, shared by the flat list and the department tree.

	ONE implementation on purpose. Two would drift, and the drift would show as
	a department's roll-up disagreeing with the very people listed underneath it
	— which is the shape of defect this module has already paid for twice today
	(the filing guard against the row scope, and the tier check against the
	detail fence). Whatever the tree shows, the list shows.
	"""
	# Every employee on the hub. The audience for this page is group-level, so
	# there is no company predicate here — see _team_kpi_viewer for the ruling.
	# Exempted from the class guard with that reason in
	# hrms/tests/test_api_employee_reads_are_fenced.py::EXEMPT_REASONS,
	# keyed on _scored_rows since the pipeline was extracted.
	#
	# ceiling: whole-table Employee read, measured ~100 ms / ~15 MB at 25 000
	# employees (3 ms / 0.3 MB at 500); the Appraisal read below is unbounded
	# too and is the larger table at that size — not yet measured
	# upgrade: push the CALLER'S optional company/department filter arguments
	# into SQL (not the fence — there is none here by ruling) and bound the
	# Appraisal read by the resulting employee set, past ~25 000 employees
	#
	# What IS load-bearing: the row's company comes from the EMPLOYEE, never
	# from Appraisal.company. The latter is a plain Link copied from the
	# Appraisal Cycle (appraisal_cycle.create_appraisals_for_cycle), has no
	# fetch_from, and validate() never reconciles the two — so it names the
	# wrong company often enough that the Company filter, the selector and the
	# Company column would all disagree with the Employee master. The row is
	# about a person, so the person's company governs it.
	# `reports` is the manager's chain as _scope already resolved it — not
	# recombined here. That recombination, done three times with slightly
	# different arithmetic, is what leaked.
	employee_filters = {}
	if reports is not None:
		employee_filters = {"name": ("in", reports or [""])}

	employees = {
		row.name: row
		for row in frappe.get_all(
			"Employee",
			filters=employee_filters,
			fields=["name", "employee_name", "designation", "department", "company", "image"],
		)
	}

	appraisal_filters = {"docstatus": ("<", 2)}
	if reports is not None:
		# Bound the read to the chain rather than filtering a whole-table result
		# in Python against a handful of employees.
		appraisal_filters["employee"] = ("in", reports or [""])

	appraisals = frappe.get_all(
		"Appraisal",
		filters=appraisal_filters,
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


#: Employees with no department at all. They exist (Employee.department is not
#: mandatory), and without a home in the tree they would vanish from it while
#: still counting in the flat list — the two would disagree about the same
#: people, which is the whole failure this module keeps paying for.
NO_DEPARTMENT = "__none__"


def _department_index() -> dict:
	"""Every department by name, with its nested-set bounds. Frappe keeps
	Department as a real tree (`parent_department`, `is_group`, `lft`/`rgt`), so
	"is this inside that subtree" is a range test, not a recursive walk."""
	return {
		row.name: row
		for row in frappe.get_all(
			"Department",
			fields=["name", "parent_department", "is_group", "lft", "rgt", "company"],
		)
	}


@frappe.whitelist(methods=["GET", "POST"])
def get_department_kpi(
	parent: str | None = None,
	year: str | int | None = None,
	cycle: str | None = None,
	company: str | None = None,
) -> dict:
	"""ONE LEVEL of the department tree, with each child's roll-up.

	The CEO and HR navigate STRUCTURE: All Departments -> Sales -> Sales East ->
	a person. Every level answers "how is this part of the company doing, and
	what is directly inside it". A manager gets no door here — their scope is
	PEOPLE, not org structure, and the flat list already serves it.

	THE ROLL-UP IS AN AVERAGE OVER PEOPLE IN THE SUBTREE, which is what makes it
	headcount-weighted without any weighting arithmetic: a department of fifty
	pulls twenty-five times as hard as one of two. Averaging the
	sub-departments' averages instead would give a two-person team the same vote
	as a fifty-person one. Decision on record (Nabil, 13 Sep 2026).

	The ERP stores NO department score — Appraisal carries per-person scores and
	there is no department-level doctype anywhere. This number is computed for
	display, never fetched and never stored, so there is nothing to keep in sync.

	Rows come from `_scored_rows`, the same pipeline the flat list uses, so a
	department's roll-up cannot disagree with the people listed underneath it.
	"""
	viewer, reports = _scope()
	if viewer not in (VIEWER_CEO, VIEWER_HR):
		logger.warning("[kpi] department tree refused for user=%s (tier %s)", frappe.session.user, viewer)
		frappe.throw(
			_("The department view is available to the Chief Executive Officer and to HR."),
			frappe.PermissionError,
		)

	if company and not frappe.db.exists("Company", company):
		frappe.throw(_("No such company: {0}.").format(company))
	if parent is not None and not isinstance(parent, str):
		frappe.throw(_("A department must be named."), frappe.PermissionError)

	data = _scored_rows(viewer, reports, year, cycle, company, None)
	rows = data["rows"]
	index = _department_index()

	if parent and parent != NO_DEPARTMENT and parent not in index:
		frappe.throw(_("No such department: {0}.").format(parent))

	# ceiling: people_under is O(children x rows) — measured on a 302-department
	# site: the index costs 1 ms, the root's tree maths 23 ms at 500 rows,
	# 132 ms at 3 000, 431 ms at 10 000
	# upgrade: index the rows by department once and sum over the lft ranges,
	# when a single year's appraisal count passes ~3 000
	def people_under(name):
		"""Everyone whose department sits inside this subtree."""
		if name == NO_DEPARTMENT:
			return [r for r in rows if not r["department"]]
		node = index.get(name)
		if not node:
			return []
		out = []
		for r in rows:
			child = index.get(r["department"]) if r["department"] else None
			if child and node.lft <= child.lft and child.rgt <= node.rgt:
				out.append(r)
		return out

	def roll_up(people):
		if not people:
			return {"headcount": 0, "average_score": 0.0, "top_score": 0.0}
		scores = [r["total_score"] for r in people]
		return {
			"headcount": len(people),
			"average_score": flt(sum(scores) / len(scores), 1),
			"top_score": max(scores),
		}

	roots = [d for d in index.values() if not d.parent_department]
	root_name = roots[0].name if roots else None
	at_root = not parent or parent == root_name

	here = root_name if at_root else parent
	people_here = rows if at_root else people_under(parent)
	children = [d for d in index.values() if d.parent_department == (root_name if at_root else parent)]

	# A department with NOBODY APPRAISED under it is not offered. A stock
	# ERPNext site seeds a full department set per company, so the root of a
	# multi-company hub lists hundreds of them and all but a handful are empty:
	# the two that matter are buried, and every empty one is a dead end that
	# opens on nothing. Same rule this module already applies to the company and
	# department selectors — an option that can only ever return nothing reads
	# as broken data, not as a choice.
	#
	# The headcount is on every row that IS offered, so "Sales has nobody
	# appraised this cycle" is still answerable: Sales simply is not in the list
	# for that cycle, and the node's own summary says how many people it counts.
	departments = sorted(
		(
			node
			for child in children
			if (
				node := {
					"name": child.name,
					"label": child.name,
					"is_group": bool(child.is_group),
					**roll_up(people_under(child.name)),
				}
			)["headcount"]
		),
		key=lambda d: (-d["headcount"], d["label"]),
	)
	# Only at the root, and only when they exist: somebody with no department
	# belongs nowhere else, and an empty bucket reads as broken data.
	if at_root:
		orphans = [r for r in rows if not r["department"]]
		if orphans:
			departments.append(
				{
					"name": NO_DEPARTMENT,
					"label": _("No department"),
					"is_group": False,
					**roll_up(orphans),
				}
			)

	# The people standing at THIS node — directly in it, not inside a child.
	people = (
		[r for r in rows if not r["department"]]
		if here == NO_DEPARTMENT
		else [r for r in rows if r["department"] == here]
	)

	# The sentinel node is not IN the tree, so the walk below cannot reach it and
	# cannot produce a crumb for it. Without seeding, "No department" rendered a
	# one-item breadcrumb — no clickable ancestor, and no other way back: the
	# filters refetch the same node and switching tabs does not refetch at all.
	# A page reload was the only exit.
	trail = [{"name": NO_DEPARTMENT, "label": _("No department")}] if parent == NO_DEPARTMENT else []
	walk = None if at_root else parent
	seen = set()
	while walk and walk in index and walk not in seen:
		# `seen` bounds the walk. A parent_department cycle is refused by the
		# ORM (NestedSetRecursionError) but reachable through db.set_value, and
		# an unbounded walk there does not terminate.
		seen.add(walk)
		trail.append({"name": walk, "label": walk})
		walk = index[walk].parent_department
	# Only if the walk did not already arrive there: it stops when a node's
	# parent is empty, which IS the root, so appending unconditionally rendered
	# "All Departments > All Departments > Sales" and handed Vue duplicate keys.
	if root_name and (not trail or trail[-1]["name"] != root_name):
		trail.append({"name": root_name, "label": root_name})
	trail.reverse()

	logger.info(
		"[kpi] department tree user=%s node=%s children=%d people=%d",
		frappe.session.user,
		here or "root",
		len(departments),
		len(people),
	)

	return {
		"viewer_mode": viewer,
		"node": {
			"name": here,
			"label": _("No department") if here == NO_DEPARTMENT else (here or _("All Departments")),
			"is_root": at_root,
		},
		"breadcrumb": trail,
		"summary": roll_up(people_here),
		"departments": departments,
		"people": sorted(people, key=lambda r: -r["total_score"]),
		"companies": data["companies"],
		"selected_company": data["selected_company"],
		"years": data["years"],
		"cycles": data["cycles"],
		"selected_year": data["selected_year"],
		"selected_cycle": data["selected_cycle"],
	}


@frappe.whitelist(methods=["GET", "POST"])
def get_team_kpi(
	year: str | int | None = None,
	cycle: str | None = None,
	department: str | None = None,
	company: str | None = None,
) -> dict:
	"""Read-only appraisal scores for whatever the caller's tier admits: their
	own reporting chain (manager), or every company on the hub (CEO, HR).

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
	viewer, reports = _scope()
	if not viewer:
		logger.warning("[kpi] team view refused for user=%s", frappe.session.user)
		frappe.throw(
			_(
				"The Team KPI view is available to the Chief Executive Officer, to HR, and to managers for their own team."
			),
			frappe.PermissionError,
		)

	if company and not frappe.db.exists("Company", company):
		# An empty table reads as "nobody was appraised", so a company that does
		# not exist has to say so rather than look like an answer.
		frappe.throw(_("No such company: {0}.").format(company))

	return _scored_rows(viewer, reports, year, cycle, company, department)
