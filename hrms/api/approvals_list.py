"""Everything waiting on the caller's decision, as rows (the Approvals page).

Owner ruling, 23 Sep 2026: approvals appear only where they can be done, and
the Approvals page is that place (audit-flows 4B, AUDIT-PLAN P1-B). Home's
Waiting on you gives counts; this gives the rows behind them, oldest first,
each saying who, what, when and why, in the person's words.

A row is listed only when `approval._is_routed_approver` admits it — the same
check Home's count (`needs_you`) and `approval.decide` use — so the page can
never show a request the approver cannot decide, or hide one Home counted.
Session-scoped: the caller is never a parameter.
"""

import logging

import frappe

from hrms.api.approval import DECIDE_THEN_SUBMIT, _is_routed_approver

logger = logging.getLogger(__name__)

#: Rows examined per type before the list stops (the same bound needs_you
#: uses): an HR operator is routed everything, and every candidate costs a
#: routed-approver check. Past it the page says the list is longer.
SCAN_CAP = 50

#: The person's word for each type (glossary: "Time off", "Overtime" …).
KIND = {
	"Leave Application": "Time off",
	"Expense Claim": "Expense",
	"Shift Request": "Shift change",
	"Attendance Request": "Fix a day",
	"OT Request": "Overtime",
	"Replacement Leave Claim": "Replacement leave",
	"Compensatory Leave Request": "Time off in lieu",
}


def _types_on_site() -> list[str]:
	"""Request types this site has; a missing app must not 500 the page."""
	return [dt for dt in DECIDE_THEN_SUBMIT if frappe.db.exists("DocType", dt)]


def _hours(hours) -> str:
	minutes = round((float(hours or 0)) * 60)
	h, m = divmod(minutes, 60)
	return f"{h}h {m:02d}m" if h else f"{m}m"


def _days(n) -> str:
	n = float(n or 0)
	text = f"{n:g}"
	return f"{text} day" if n == 1 else f"{text} days"


def _row(doc) -> dict:
	"""What an approver needs to decide, in plain words. No raw field names."""
	kind = KIND.get(doc.doctype, doc.doctype)
	when, detail, reason = "", "", ""
	if doc.doctype == "Leave Application":
		when = _range(doc.get("from_date"), doc.get("to_date"))
		detail = f"{doc.get('leave_type')} · {_days(doc.get('total_leave_days'))}"
		reason = doc.get("description") or ""
	elif doc.doctype == "OT Request":
		when = str(doc.get("ot_date") or "")
		detail = _hours(doc.get("claimed_hours"))
		reason = doc.get("explanation") or ""
	elif doc.doctype == "Expense Claim":
		detail = f"{frappe.utils.fmt_money(doc.get('grand_total') or doc.get('total_claimed_amount') or 0)}"
		reason = doc.get("remark") or ""
	elif doc.doctype == "Shift Request":
		when = _range(doc.get("from_date"), doc.get("to_date"))
		detail = doc.get("shift_type") or ""
	elif doc.doctype == "Attendance Request":
		when = _range(doc.get("from_date"), doc.get("to_date"))
		detail = doc.get("reason") or ""
		reason = doc.get("explanation") or ""
	elif doc.doctype == "Replacement Leave Claim":
		when = str(doc.get("bank_month") or "")
		detail = _days(doc.get("claimed_days"))
		reason = doc.get("explanation") or ""
	elif doc.doctype == "Compensatory Leave Request":
		when = _range(doc.get("work_from_date"), doc.get("work_end_date"))
		detail = doc.get("leave_type") or ""
		reason = doc.get("reason") or ""
	return {
		"doctype": doc.doctype,
		"name": doc.name,
		"kind": kind,
		"who": doc.get("employee_name") or doc.get("employee"),
		"when": when,
		"detail": detail,
		"reason": reason,
		"modified": str(doc.get("modified") or ""),
	}


def _range(start, end) -> str:
	start, end = str(start or ""), str(end or "")
	return start if not end or end == start else f"{start} – {end}"


@frappe.whitelist(methods=["GET", "POST"])
def get_waiting_for_me() -> dict:
	rows, capped = [], False
	for doctype in _types_on_site():
		field, pending = DECIDE_THEN_SUBMIT[doctype]
		try:
			names = frappe.get_all(
				doctype,
				filters={field: pending, "docstatus": 0},
				pluck="name",
				order_by="modified asc",
				limit=SCAN_CAP + 1,
				ignore_permissions=True,
			)
		except Exception:
			# One unavailable type must not take the page down; logged by name
			# so a silent zero is never mistaken for an empty queue.
			logger.exception("[approvals_list] %s failed; skipped", doctype)
			continue
		capped = capped or len(names) > SCAN_CAP
		for name in names[:SCAN_CAP]:
			doc = frappe.get_doc(doctype, name)
			if _is_routed_approver(doc):
				rows.append(_row(doc))
	# Oldest first: the one waiting longest is the one to decide next.
	rows.sort(key=lambda row: row["modified"])
	logger.info("[approvals_list] user=%s rows=%d capped=%s", frappe.session.user, len(rows), capped)
	return {"rows": rows, "capped": capped}
