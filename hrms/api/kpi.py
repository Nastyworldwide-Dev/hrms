# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import logging

import frappe
from frappe import _
from frappe.utils import flt

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

HISTORY_LIMIT = 6


def _get_session_employee() -> str:
	employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user, "status": "Active"}, "name")
	if not employee:
		frappe.throw(_("No active Employee record is linked to your user."), frappe.PermissionError)
	return employee


@frappe.whitelist()
def get_my_kpi_dashboard() -> dict:
	"""Personal KRA/KPI dashboard for the logged-in employee (PWA "My KPI").

	Deliberately takes no arguments: the appraisal visibility hooks in
	appraisal.py do not cover whitelisted endpoints, so this endpoint is
	scoped to the session user's own Employee by construction.
	"""
	employee = _get_session_employee()
	emp = frappe.db.get_value(
		"Employee", employee, ["name", "employee_name", "designation", "image"], as_dict=True
	)

	history = frappe.get_all(
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
		],
		order_by="end_date desc, modified desc",
		limit=HISTORY_LIMIT,
	)
	logger.info(
		"[kpi] dashboard user=%s employee=%s appraisals=%d",
		frappe.session.user,
		employee,
		len(history),
	)

	if not history:
		return {
			"employee": emp,
			"current": None,
			"previous_score": None,
			"history": [],
			"feedback": {"count": 0},
		}

	doc = frappe.get_doc("Appraisal", history[0].name)
	# Defense in depth: the own-employee rule in Appraisal.has_permission
	# must allow this read; fail loudly if the visibility scope ever changes.
	frappe.has_permission("Appraisal", doc=doc, throw=True)

	kras = [{field: row.get(field) for field in KRA_ROW_FIELDS} for row in doc.appraisal_kra]

	previous_score = next((flt(h.pms_total_score) for h in history[1:] if h.docstatus == 1), None)

	feedback_count = frappe.db.count(
		"Employee Performance Feedback", {"employee": employee, "appraisal": doc.name}
	)

	trend = [
		{
			"appraisal": h.name,
			"cycle": h.appraisal_cycle,
			"end_date": h.end_date,
			"total_score": flt(h.pms_total_score),
			"grade": h.overall_grade,
		}
		for h in reversed(history)
	]

	return {
		"employee": emp,
		"current": {
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
		},
		"previous_score": previous_score,
		"history": trend,
		"feedback": {"count": feedback_count},
	}
